from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.gemini_agent import confirm_rule, explain_infeasible, propose_from_override
from app.models import (
    CalloutCandidate,
    CalloutRequest,
    Infeasibility,
    OverrideEvent,
    Roster,
)
from app.seed import NUM_DAYS, WARD, nurses, period_dates, weekday_name
from app.solver import solve
from app.store import add_rule, load_history, load_rules, nurse_map, record_cycle

app = FastAPI(title="Askonce", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION: dict = {
    "roster": None,
    "overrides_this_cycle": 0,
}


class ConfirmBody(BaseModel):
    override: OverrideEvent
    option_id: str
    free_text: str = ""
    manager: str = "Nurse Manager Sato"


class VoiceBody(BaseModel):
    text: str
    manager: str = "Nurse Manager Sato"


def _dates():
    return [
        {
            "index": i,
            "iso": d.isoformat(),
            "label": f"{d.strftime('%a')} {d.day}",
            "weekday": d.weekday(),
            "weekend": d.weekday() >= 5,
        }
        for i, d in enumerate(period_dates())
    ]


@app.get("/api/ward")
def ward():
    return {
        "ward": WARD,
        "nurses": [n.model_dump() for n in nurses()],
        "days": _dates(),
        "num_days": NUM_DAYS,
        "pitch": "The roster that learns the rules nobody wrote down.",
        "rules": [r.model_dump() for r in load_rules()],
        "history": load_history(),
        "overrides_this_cycle": SESSION["overrides_this_cycle"],
        "roster": SESSION["roster"].model_dump() if SESSION["roster"] else None,
    }


@app.post("/api/generate")
def generate():
    result = solve(load_rules())
    if isinstance(result, Infeasibility):
        result.summary = explain_infeasible(result.summary, result.conflicts)
        return {"ok": False, "infeasible": result.model_dump()}
    SESSION["roster"] = result
    return {"ok": True, "roster": result.model_dump()}


@app.post("/api/override/propose")
def override_propose(ov: OverrideEvent):
    SESSION["overrides_this_cycle"] += 1
    proposal = propose_from_override(ov)
    return proposal.model_dump()


@app.post("/api/override/confirm")
def override_confirm(body: ConfirmBody):
    rule = confirm_rule(body.override, body.option_id, body.free_text, body.manager)
    rules = add_rule(rule)
    result = solve(rules)
    if isinstance(result, Infeasibility):
        result.summary = explain_infeasible(result.summary, result.conflicts)
        return {"ok": False, "rule": rule.model_dump(), "infeasible": result.model_dump()}
    SESSION["roster"] = result
    record_cycle(SESSION["overrides_this_cycle"], len(rules))
    return {
        "ok": True,
        "rule": rule.model_dump(),
        "roster": result.model_dump(),
        "history": load_history(),
        "rules": [r.model_dump() for r in rules],
    }


@app.post("/api/callout")
def callout(req: CalloutRequest):
    current: Roster | None = SESSION["roster"]
    people = nurse_map()
    sick = people[req.nurse_id]
    forbidden = [(req.nurse_id, req.day_index, req.shift)]
    result = solve(
        load_rules(),
        forbidden=forbidden,
        minimize_changes_from=current,
    )
    if isinstance(result, Infeasibility):
        result.summary = explain_infeasible(result.summary, result.conflicts)
        return {"ok": False, "infeasible": result.model_dump()}

    before = {}
    if current:
        before = {(a.nurse_id, a.day_index): a.shift for a in current.assignments}
    after = {(a.nurse_id, a.day_index): a.shift for a in result.assignments}

    moved_onto = []
    for (nid, day), sh in after.items():
        if day == req.day_index and sh == req.shift and nid != req.nurse_id:
            if before.get((nid, day)) != sh:
                moved_onto.append(nid)

    candidates: list[CalloutCandidate] = []
    for nid in moved_onto or [n.id for n in nurses() if n.id != req.nurse_id]:
        n = people[nid]
        legal = not (
            req.shift == "night" and "postpartum_no_nights" in n.legal_flags
        )
        score = n.prior_callouts * 10 + n.prior_nights + n.prior_weekends * 2
        if n.role == "junior" and req.shift == "night":
            score += 20
        if not legal:
            score += 1000
        why = (
            f"Lowest fairness penalty ({n.prior_callouts} prior callouts). "
            f"{'Illegal: postpartum night ban.' if not legal else 'Legal.'}"
        )
        msg = (
            f"Hi {n.name.split()[0]}, {sick.name.split()[0]} is out "
            f"{weekday_name(req.day_index)} {req.shift}. "
            f"Can you cover? We'll credit this on the fairness ledger."
        )
        candidates.append(
            CalloutCandidate(
                nurse_id=n.id,
                name=n.name,
                score=score,
                why=why,
                legal=legal,
                message=msg,
            )
        )
    candidates.sort(key=lambda c: (not c.legal, c.score))
    SESSION["roster"] = result
    return {
        "ok": True,
        "roster": result.model_dump(),
        "candidates": [c.model_dump() for c in candidates[:5]],
        "picked": candidates[0].model_dump() if candidates else None,
    }


@app.post("/api/voice-rule")
def voice_rule(body: VoiceBody):
    """Optional scoring extra: 'Priya can't do nights while mum is in hospital.'"""
    text = body.text.lower()
    target = None
    for n in nurses():
        first = n.name.split()[0].lower()
        if first in text or n.id in text:
            target = n
            break
    if target is None:
        return {"ok": False, "error": "Could not match a nurse in that sentence."}

    # Build a synthetic Saturday-night style override from language.
    from app.models import OverrideEvent as OE

    shift = "night" if "night" in text else "day" if "day" in text else "evening"
    # Prefer next matching weekday mentioned, else first Saturday.
    day_index = 5  # first Saturday in the period starting Monday
    for token, wd in [("saturday", 5), ("sunday", 6), ("friday", 4), ("monday", 0)]:
        if token in text:
            for i, d in enumerate(period_dates()):
                if d.weekday() == wd:
                    day_index = i
                    break
    ov = OE(
        nurse_id=target.id,
        day_index=day_index,
        from_shift=shift,
        to_shift="off",
        manager=body.manager,
    )
    proposal = propose_from_override(ov)
    return {"ok": True, "override": ov.model_dump(), "proposal": proposal.model_dump()}


class ForceBody(BaseModel):
    nurse_id: str
    day_index: int = 0
    shift: str = "night"


@app.post("/api/force")
def force_assign(body: ForceBody):
    """Try an illegal pin (Yamada on nights) so refusal is the demo, not a crash."""
    result = solve(load_rules(), locks=[(body.nurse_id, body.day_index, body.shift)])
    if isinstance(result, Infeasibility):
        result.summary = explain_infeasible(result.summary, result.conflicts)
        return {"ok": False, "infeasible": result.model_dump()}
    SESSION["roster"] = result
    return {"ok": True, "roster": result.model_dump()}


@app.get("/api/health")
def health():
    return {"ok": True}
