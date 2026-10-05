from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv

from app.models import (
    LearnedConstraint,
    OverrideEvent,
    ProposedRule,
)
from app.seed import period_dates, weekday_name
from app.store import load_rules, nurse_map

load_dotenv()


def _existing_explains(ov: OverrideEvent, rules: list[LearnedConstraint]) -> LearnedConstraint | None:
    wd = period_dates()[ov.day_index].weekday()
    for r in rules:
        if ov.nurse_id not in r.nurse_ids:
            continue
        if r.kind == "block_cell" and r.day_index == ov.day_index:
            if r.shift_type in (ov.from_shift, None):
                return r
        if r.kind in ("block_shift_type", "block_weekday", "prefer_off_weekday"):
            if r.weekday is not None and r.weekday != wd:
                continue
            if r.shift_type and r.shift_type != ov.from_shift and r.shift_type != "off":
                continue
            return r
    return None


def propose_from_override(ov: OverrideEvent) -> ProposedRule:
    rules = load_rules()
    known = _existing_explains(ov, rules)
    people = nurse_map()
    nurse = people[ov.nurse_id]
    day = period_dates()[ov.day_index]
    label = f"{nurse.name} {weekday_name(ov.day_index)} {ov.from_shift} → {ov.to_shift}"

    if known:
        return ProposedRule(
            question=f"This move is already explained by a known rule: {known.reason}",
            options=[],
            draft=known,
            unexplained=False,
            why_unexplained=f"Matched rule {known.id} taught by {known.taught_by}.",
        )

    why = (
        f"{nurse.name} was on {ov.from_shift} {day.strftime('%a')} {day.day} {day.strftime('%b')}. "
        f"The manager moved them to {ov.to_shift}. "
        "No learned or legal rule forbids the original cell, so the solver was allowed to put them there. "
        "The override is therefore a missing rule, not a bug."
    )

    draft = _heuristic_draft(ov, nurse.name)
    question = (
        f"That assignment didn't break any rule I know — so I'm missing one. "
        f"Why shouldn't {nurse.name} work {weekday_name(ov.day_index)} {ov.from_shift}s?"
    )

    options = [
        {
            "id": "permanent_weekday",
            "label": f"Permanent: never {weekday_name(ov.day_index)} {ov.from_shift}s",
            "scope": "permanent",
            "kind": "block_weekday",
        },
        {
            "id": "this_period",
            "label": "Only this 14-day roster",
            "scope": "this_period",
            "kind": "block_weekday",
        },
        {
            "id": "once",
            "label": "Just this one shift",
            "scope": "once",
            "kind": "block_cell",
        },
    ]

    gemini = _ask_gemini(ov, nurse.name, why, question)
    if gemini:
        question = gemini.get("question", question)
        if gemini.get("reason"):
            draft.reason = gemini["reason"]
        if gemini.get("kind") in (
            "block_shift_type",
            "block_weekday",
            "block_cell",
            "avoid_pair",
            "max_nights",
            "prefer_off_weekday",
        ):
            draft.kind = gemini["kind"]

    draft.source_override = label
    return ProposedRule(
        question=question,
        options=options,
        draft=draft,
        unexplained=True,
        why_unexplained=why,
    )


def confirm_rule(
    ov: OverrideEvent,
    option_id: str,
    free_text: str,
    manager: str,
) -> LearnedConstraint:
    people = nurse_map()
    nurse = people[ov.nurse_id]
    scope = "permanent"
    kind = "block_weekday"
    if option_id == "once":
        scope = "once"
        kind = "block_cell"
    elif option_id == "this_period":
        scope = "this_period"
        kind = "block_weekday"

    reason = free_text.strip() or f"{nurse.name} should not work {weekday_name(ov.day_index)} {ov.from_shift}s"
    rule = LearnedConstraint(
        id=f"lr_{uuid.uuid4().hex[:8]}",
        kind=kind,
        nurse_ids=[ov.nurse_id],
        shift_type=ov.from_shift,
        weekday=None if kind == "block_cell" else period_dates()[ov.day_index].weekday(),
        day_index=ov.day_index if kind == "block_cell" else None,
        hard=True,
        scope=scope,
        taught_by=manager,
        taught_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        reason=reason,
        raw_answer=free_text,
        source_override=f"{nurse.name} {weekday_name(ov.day_index)} {ov.from_shift} → {ov.to_shift}",
    )
    return rule


def _heuristic_draft(ov: OverrideEvent, nurse_name: str) -> LearnedConstraint:
    wd = period_dates()[ov.day_index].weekday()
    return LearnedConstraint(
        id="draft",
        kind="block_weekday",
        nurse_ids=[ov.nurse_id],
        shift_type=ov.from_shift,
        weekday=wd,
        hard=True,
        scope="permanent",
        taught_by=ov.manager,
        taught_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        reason=f"{nurse_name} should not work {weekday_name(ov.day_index)} {ov.from_shift}s",
        raw_answer="",
        source_override="",
    )


def _ask_gemini(ov: OverrideEvent, nurse_name: str, why: str, question: str) -> dict | None:
    key = os.getenv("GEMINI_API_KEY", "")
    if not key or key.startswith("your_"):
        return None
    try:
        from google import genai

        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        client = genai.Client(api_key=key)
        prompt = f"""You are Askonce, a ward roster agent. A manager overrode the solver.
Nurse: {nurse_name}
Move: day {ov.day_index} ({weekday_name(ov.day_index)}) {ov.from_shift} → {ov.to_shift}
Why this is unexplained: {why}

Return JSON only:
{{"question": "one short question to the manager",
  "reason": "one sentence rule in plain English",
  "kind": "block_weekday"}}
Keep the question under 25 words. Do not mention solvers or CP-SAT.
"""
        resp = client.models.generate_content(model=model, contents=prompt)
        text = (resp.text or "").strip()
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
    except Exception:
        return None
    return None


def explain_infeasible(summary: str, conflicts: list[str]) -> str:
    key = os.getenv("GEMINI_API_KEY", "")
    fallback = summary + " " + " ".join(conflicts[:2])
    if not key or key.startswith("your_"):
        return (
            "You cannot cover that night without either exceeding the night cap "
            "or assigning Aiko Yamada, who cannot work nights under the postpartum rule. "
            "Choose one: drop the newest learned rule, or pull a charge onto nights."
        )
    try:
        from google import genai

        client = genai.Client(api_key=key)
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        resp = client.models.generate_content(
            model=model,
            contents=(
                "Turn this solver failure into two legal choices a nurse manager understands. "
                "No jargon. Under 60 words.\n"
                f"{summary}\n" + "\n".join(conflicts)
            ),
        )
        return (resp.text or fallback).strip()
    except Exception:
        return fallback
