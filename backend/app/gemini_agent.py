from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from app import llm
from app.models import LearnedConstraint, OverrideEvent, ProposedRule, Shift
from app.seed import first_index_for_weekday, nurses, period_dates, weekday_name
from app.store import load_rules, nurse_map


class GeminiRuleCopy(BaseModel):
    question: str = Field(description="One short question to the manager, under 25 words.")
    reason: str = Field(description="The unwritten rule in one plain English sentence.")


class GeminiVoiceParse(BaseModel):
    nurse_id: str
    shift: Shift = "night"
    weekday: int | None = None
    reason: str = ""


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
            used_gemini=False,
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
    used = False
    gemini = _ask_gemini_copy(ov, nurse.name, why)
    if gemini:
        used = True
        question = gemini.question or question
        if gemini.reason:
            draft.reason = gemini.reason

    draft.source_override = label
    return ProposedRule(
        question=question,
        options=_options(ov),
        draft=draft,
        unexplained=True,
        why_unexplained=why,
        used_gemini=used,
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

    reason = (
        free_text.strip()
        or f"{nurse.name} should not work {weekday_name(ov.day_index)} {ov.from_shift}s"
    )
    return LearnedConstraint(
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


def parse_voice(text: str, manager: str) -> tuple[OverrideEvent, str] | None:
    parsed = _ask_gemini_voice(text) or _heuristic_voice(text)
    if parsed is None:
        return None
    nurse_id = parsed.nurse_id
    if nurse_id not in nurse_map():
        return None
    wd = parsed.weekday if parsed.weekday is not None else 5
    day_index = first_index_for_weekday(wd)
    ov = OverrideEvent(
        nurse_id=nurse_id,
        day_index=day_index,
        from_shift=parsed.shift if parsed.shift != "off" else "night",
        to_shift="off",
        manager=manager,
    )
    return ov, parsed.reason


def _options(ov: OverrideEvent) -> list[dict]:
    return [
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


def _heuristic_voice(text: str) -> GeminiVoiceParse | None:
    lower = text.lower()
    target = None
    for n in nurses():
        first = n.name.split()[0].lower()
        if first in lower or n.id in lower:
            target = n
            break
    if target is None:
        return None
    shift: Shift = "night" if "night" in lower else "day" if "day" in lower else "evening"
    weekday = 5
    for token, wd in [
        ("saturday", 5),
        ("sunday", 6),
        ("friday", 4),
        ("monday", 0),
        ("tuesday", 1),
        ("wednesday", 2),
        ("thursday", 3),
    ]:
        if token in lower:
            weekday = wd
            break
    return GeminiVoiceParse(
        nurse_id=target.id,
        shift=shift,
        weekday=weekday,
        reason=text.strip(),
    )


def _ask_gemini_copy(ov: OverrideEvent, nurse_name: str, why: str) -> GeminiRuleCopy | None:
    if not llm.gemini_ready():
        return None
    try:
        from google.genai import types

        prompt = (
            "You are Askonce. A ward manager overrode the roster. "
            "Ask ONE question so the unwritten rule can be saved. "
            "Do not mention solvers, CP-SAT, or JSON.\n"
            f"Nurse: {nurse_name}\n"
            f"Move: {weekday_name(ov.day_index)} {ov.from_shift} → {ov.to_shift}\n"
            f"Why unexplained: {why}"
        )
        resp = llm.client().models.generate_content(
            model=llm.model_name(),
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiRuleCopy,
            ),
        )
        text = (resp.text or "").strip()
        return GeminiRuleCopy.model_validate_json(text)
    except Exception:
        return None


def _ask_gemini_voice(text: str) -> GeminiVoiceParse | None:
    if not llm.gemini_ready():
        return None
    try:
        from google.genai import types

        roster = ", ".join(f"{n.id}={n.name}" for n in nurses())
        prompt = (
            "Parse this manager sentence into a roster constraint. "
            f"Known nurses: {roster}\n"
            f"Sentence: {text}\n"
            "weekday is 0=Mon ... 6=Sun. Prefer Saturday if unspecified weekend."
        )
        resp = llm.client().models.generate_content(
            model=llm.model_name(),
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiVoiceParse,
            ),
        )
        return GeminiVoiceParse.model_validate_json((resp.text or "").strip())
    except Exception:
        return None


def explain_infeasible(summary: str, conflicts: list[str]) -> str:
    fallback = (
        "You cannot cover that night without either exceeding the night cap "
        "or assigning Aiko Yamada, who cannot work nights under the postpartum rule. "
        "Choose one: drop the newest learned rule, or pull a charge onto nights."
    )
    if not llm.gemini_ready():
        return fallback
    try:
        from google.genai import types

        resp = llm.client().models.generate_content(
            model=llm.model_name(),
            contents=(
                "Turn this roster failure into two legal choices a nurse manager understands. "
                "No jargon. Under 60 words.\n"
                f"{summary}\n" + "\n".join(conflicts)
            ),
            config=types.GenerateContentConfig(max_output_tokens=120),
        )
        return (resp.text or fallback).strip()
    except Exception:
        return fallback
