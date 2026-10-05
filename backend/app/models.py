from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Shift = Literal["day", "evening", "night", "off"]
Scope = Literal["once", "this_period", "permanent"]
ConstraintKind = Literal[
    "block_shift_type",
    "block_weekday",
    "block_cell",
    "avoid_pair",
    "max_nights",
    "prefer_off_weekday",
]


class Nurse(BaseModel):
    id: str
    name: str
    role: Literal["charge", "rn", "junior"]
    legal_flags: list[str] = Field(default_factory=list)
    notes: str = ""
    prior_callouts: int = 0
    prior_nights: int = 0
    prior_weekends: int = 0


class LearnedConstraint(BaseModel):
    id: str
    kind: ConstraintKind
    nurse_ids: list[str]
    shift_type: Shift | None = None
    weekday: int | None = None  # 0=Mon ... 6=Sun
    day_index: int | None = None
    hard: bool = True
    scope: Scope = "permanent"
    taught_by: str
    taught_at: str
    reason: str
    raw_answer: str
    source_override: str


class CellAssignment(BaseModel):
    nurse_id: str
    day_index: int
    shift: Shift


class Roster(BaseModel):
    assignments: list[CellAssignment]
    objective: int = 0
    status: Literal["optimal", "feasible", "infeasible"] = "optimal"
    coverage_ok: bool = True
    stats: dict = Field(default_factory=dict)


class OverrideEvent(BaseModel):
    nurse_id: str
    day_index: int
    from_shift: Shift
    to_shift: Shift
    manager: str = "Nurse Manager Sato"


class ProposedRule(BaseModel):
    question: str
    options: list[dict]
    draft: LearnedConstraint
    unexplained: bool
    why_unexplained: str


class CalloutRequest(BaseModel):
    nurse_id: str
    day_index: int
    shift: Shift
    reason: str = "called in sick"


class CalloutCandidate(BaseModel):
    nurse_id: str
    name: str
    score: int
    why: str
    legal: bool
    message: str


class Infeasibility(BaseModel):
    summary: str
    conflicts: list[str]
    legal_choices: list[str]
