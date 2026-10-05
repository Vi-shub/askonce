from __future__ import annotations

from ortools.sat.python import cp_model

from app.models import CellAssignment, Infeasibility, LearnedConstraint, Roster, Shift
from app.seed import (
    COVERAGE,
    MAX_NIGHTS,
    MAX_SHIFTS,
    NUM_DAYS,
    SHIFTS,
    nurses,
    period_dates,
)


def _shift_index(shift: Shift) -> int | None:
    if shift == "off":
        return None
    return SHIFTS.index(shift)


def solve(
    rules: list[LearnedConstraint],
    locks: list[tuple[str, int, Shift]] | None = None,
    forbidden: list[tuple[str, int, Shift]] | None = None,
    minimize_changes_from: Roster | None = None,
) -> Roster | Infeasibility:
    staff = nurses()
    n_nurses = len(staff)
    model = cp_model.CpModel()

    # works[n][d][s] == 1 if nurse n works shift s on day d
    works = [
        [
            [model.new_bool_var(f"n{n}_d{d}_{s}") for s in range(len(SHIFTS))]
            for d in range(NUM_DAYS)
        ]
        for n in range(n_nurses)
    ]

    nid = {nurse.id: i for i, nurse in enumerate(staff)}

    # At most one shift per day.
    for n in range(n_nurses):
        for d in range(NUM_DAYS):
            model.add(sum(works[n][d][s] for s in range(len(SHIFTS))) <= 1)

    # Coverage.
    for d in range(NUM_DAYS):
        for s, name in enumerate(SHIFTS):
            model.add(sum(works[n][d][s] for n in range(n_nurses)) == COVERAGE[name])

    # At least one charge on nights.
    charge = [i for i, n in enumerate(staff) if n.role == "charge"]
    for d in range(NUM_DAYS):
        model.add(sum(works[i][d][2] for i in charge) >= 1)

    # Hours / nights caps.
    for n, nurse in enumerate(staff):
        nights = sum(works[n][d][2] for d in range(NUM_DAYS))
        total = sum(works[n][d][s] for d in range(NUM_DAYS) for s in range(len(SHIFTS)))
        model.add(nights <= MAX_NIGHTS)
        model.add(total <= MAX_SHIFTS)
        if "postpartum_no_nights" in nurse.legal_flags:
            for d in range(NUM_DAYS):
                model.add(works[n][d][2] == 0)

    # No night then day.
    for n in range(n_nurses):
        for d in range(NUM_DAYS - 1):
            model.add(works[n][d][2] + works[n][d + 1][0] <= 1)

    # Learned rules.
    for rule in rules:
        _apply_rule(model, works, nid, rule)

    # Locks / forbids (callouts, manager pins).
    for nurse_id, day, shift in locks or []:
        si = _shift_index(shift)
        n = nid[nurse_id]
        if si is None:
            for s in range(len(SHIFTS)):
                model.add(works[n][day][s] == 0)
        else:
            model.add(works[n][day][si] == 1)

    for nurse_id, day, shift in forbidden or []:
        si = _shift_index(shift)
        n = nid[nurse_id]
        if si is None:
            continue
        model.add(works[n][day][si] == 0)

    # Objective: even nights + weekends, fairness ledger, optional stability.
    obj = []
    for n, nurse in enumerate(staff):
        nights = sum(works[n][d][2] for d in range(NUM_DAYS))
        weekends = []
        for d, dt in enumerate(period_dates()):
            if dt.weekday() >= 5:
                weekends.append(sum(works[n][d][s] for s in range(len(SHIFTS))))
        # Penalise loading people who already carry unsociable history.
        obj.append(nights * (3 + nurse.prior_nights // 4))
        obj.append(sum(weekends) * (4 + nurse.prior_weekends))
        obj.append(nights * nurse.prior_callouts)

    if minimize_changes_from is not None:
        prev = {
            (a.nurse_id, a.day_index): a.shift for a in minimize_changes_from.assignments
        }
        for n, nurse in enumerate(staff):
            for d in range(NUM_DAYS):
                old = prev.get((nurse.id, d), "off")
                si = _shift_index(old)
                if si is None:
                    working = sum(works[n][d][s] for s in range(len(SHIFTS)))
                    obj.append(working * 12)
                else:
                    # Pay if they are not on the same shift.
                    obj.append((1 - works[n][d][si]) * 12)

    model.minimize(sum(obj))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 8.0
    solver.parameters.num_search_workers = 8
    result = solver.solve(model)

    if result not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return Infeasibility(
            summary="No legal roster exists with the current rules.",
            conflicts=_diagnose(rules, locks, forbidden),
            legal_choices=_choices(rules, locks, forbidden),
        )

    assignments: list[CellAssignment] = []
    night_counts: dict[str, int] = {}
    for n, nurse in enumerate(staff):
        night_counts[nurse.id] = 0
        for d in range(NUM_DAYS):
            placed = False
            for s, name in enumerate(SHIFTS):
                if solver.value(works[n][d][s]):
                    assignments.append(
                        CellAssignment(nurse_id=nurse.id, day_index=d, shift=name)
                    )
                    if name == "night":
                        night_counts[nurse.id] += 1
                    placed = True
            if not placed:
                assignments.append(
                    CellAssignment(nurse_id=nurse.id, day_index=d, shift="off")
                )

    return Roster(
        assignments=assignments,
        objective=int(solver.objective_value),
        status="optimal" if result == cp_model.OPTIMAL else "feasible",
        stats={
            "nights": night_counts,
            "wall_time_s": round(solver.wall_time, 2),
        },
    )


def _apply_rule(model, works, nid: dict[str, int], rule: LearnedConstraint) -> None:
    ids = [nid[i] for i in rule.nurse_ids if i in nid]
    if not ids:
        return

    def block(n, d, s):
        if rule.hard:
            model.add(works[n][d][s] == 0)
        else:
            # Soft: just skip here; objective handles fairness already.
            pass

    if rule.kind == "block_cell" and rule.day_index is not None:
        si = _shift_index(rule.shift_type or "night")
        if si is not None:
            for n in ids:
                block(n, rule.day_index, si)
        return

    if rule.kind in ("block_shift_type", "prefer_off_weekday", "block_weekday"):
        si = _shift_index(rule.shift_type) if rule.shift_type and rule.shift_type != "off" else None
        for n in ids:
            for d in range(NUM_DAYS):
                wd = period_dates()[d].weekday()
                if rule.weekday is not None and wd != rule.weekday:
                    continue
                if si is None:
                    # block whole day
                    for s in range(len(SHIFTS)):
                        block(n, d, s)
                else:
                    block(n, d, si)
        return

    if rule.kind == "max_nights":
        for n in ids:
            model.add(sum(works[n][d][2] for d in range(NUM_DAYS)) <= 2)
        return

    if rule.kind == "avoid_pair" and len(ids) >= 2:
        a, b = ids[0], ids[1]
        for d in range(NUM_DAYS):
            for s in range(len(SHIFTS)):
                model.add(works[a][d][s] + works[b][d][s] <= 1)


def _diagnose(rules, locks, forbidden) -> list[str]:
    lines = [
        "Night coverage needs 3 people and at least one charge.",
        "Aiko Yamada cannot work nights (postpartum / nursing legal flag).",
        f"{len(rules)} learned rule(s) are also hard constraints.",
    ]
    if forbidden:
        lines.append(f"{len(forbidden)} callout/forbid lock(s) remove extra people from that cell.")
    if locks:
        lines.append(f"{len(locks)} pin(s) force someone onto a cell.")
    return lines


def _choices(rules, locks, forbidden) -> list[str]:
    return [
        "Relax the newest learned rule (keep it as this-period only).",
        "Allow a charge to move onto the uncovered night (overtime / fairness cost).",
        "Do not cover this cell with the current legal set — escalate to the float pool.",
    ]
