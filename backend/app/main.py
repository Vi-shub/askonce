from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import llm
from app.gemini_agent import (
    confirm_rule,
    explain_infeasible,
    parse_voice,
    propose_from_override,
)
from app.models import (
    CalloutCandidate,
    CalloutRequest,
    Infeasibility,
    OverrideEvent,
    Roster,
)
from app.seed import (
    NUM_DAYS,
    WARD,
    first_index_for_weekday,
    nurses,
    period_dates,
    weekday_name,
)
from app.solver import solve
from app.store import (
    add_rule,
    load_history,
    load_rules,
    nurse_map,
    record_cycle,
    reset_demo_store,
)

app = FastAPI(title="Askonce", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
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


class ForceBody(BaseModel):
    nurse_id: str
    day_index: int = 0
    shift: str = "night"


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


def _payload_extra():
    return {
        "gemini": llm.gemini_ready(),
        "pitch": "The roster that learns the rules nobody wrote down.",
    }


@app.get("/api/ward")
def ward():
    return {
        "ward": WARD,
        "nurses": [n.model_dump() for n in nurses()],
        "days": _dates(),
        "num_days": NUM_DAYS,
        "rules": [r.model_dump() for r in load_rules()],
        "history": load_history(),
        "overrides_this_cycle": SESSION["overrides_this_cycle"],
        "roster": SESSION["roster"].model_dump() if SESSION["roster"] else None,
        **_payload_extra(),
    }


@app.post("/api/demo/setup")
def demo_setup():
    """Reliable three-story demo: Priya on Sat night, Daniel on a weekday night."""
    reset_demo_store()
    SESSION["overrides_this_cycle"] = 0
    sat = first_index_for_weekday(5)
    tue = first_index_for_weekday(1)
    result = solve([], locks=[("n04", sat, "night"), ("n06", tue, "night")])
    if isinstance(result, Infeasibility):
        result = solve([], locks=[("n04", sat, "night")])
    if isinstance(result, Infeasibility):
        result.summary = explain_infeasible(result.summary, result.conflicts)
        return {"ok": False, "infeasible": result.model_dump()}
    SESSION["roster"] = result
    return {
        "ok": True,
        "roster": result.model_dump(),
        "history": load_history(),
        "rules": [],
        **_payload_extra(),
    }


@app.post("/api/generate")
def generate():
    result = solve(load_rules())
    if isinstance(result, Infeasibility):
        result.summary = explain_infeasible(result.summary, result.conflicts)
        return {"ok": False, "infeasible": result.model_dump()}
    SESSION["roster"] = result
    return {"ok": True, "roster": result.model_dump(), **_payload_extra()}


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
    parsed = parse_voice(body.text, body.manager)
    if parsed is None:
        return {"ok": False, "error": "Could not match a nurse in that sentence."}
    ov, reason = parsed
    proposal = propose_from_override(ov)
    return {
        "ok": True,
        "override": ov.model_dump(),
        "proposal": proposal.model_dump(),
        "suggested_reason": reason,
        "used_gemini": proposal.used_gemini,
    }


@app.post("/api/force")
def force_assign(body: ForceBody):
    result = solve(load_rules(), locks=[(body.nurse_id, body.day_index, body.shift)])
    if isinstance(result, Infeasibility):
        result.summary = explain_infeasible(result.summary, result.conflicts)
        return {"ok": False, "infeasible": result.model_dump()}
    SESSION["roster"] = result
    return {"ok": True, "roster": result.model_dump()}


@app.get("/api/health")
def health():
    return {"ok": True, "gemini": llm.gemini_ready()}


def _static_dir() -> Path | None:
    here = Path(__file__).resolve()
    docker = here.parents[1] / "static"
    local = here.parents[2] / "frontend" / "dist"
    for candidate in (docker, local):
        if (candidate / "index.html").exists():
            return candidate
    return None


_STATIC = _static_dir()
if _STATIC is not None:
    assets = _STATIC / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/")
    def index():
        return FileResponse(_STATIC / "index.html")

    @app.get("/{full_path:path}")
    def spa(full_path: str):
        target = _STATIC / full_path
        if target.exists() and target.is_file():
            return FileResponse(target)
        return FileResponse(_STATIC / "index.html")
