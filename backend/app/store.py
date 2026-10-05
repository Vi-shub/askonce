from __future__ import annotations

import json
from pathlib import Path

from app.models import LearnedConstraint
from app.seed import nurses

DATA = Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(exist_ok=True)
RULES_PATH = DATA / "learned_rules.json"
HISTORY_PATH = DATA / "override_history.json"


def load_rules() -> list[LearnedConstraint]:
    if not RULES_PATH.exists():
        return []
    raw = json.loads(RULES_PATH.read_text(encoding="utf-8"))
    return [LearnedConstraint.model_validate(r) for r in raw]


def save_rules(rules: list[LearnedConstraint]) -> None:
    RULES_PATH.write_text(
        json.dumps([r.model_dump() for r in rules], indent=2),
        encoding="utf-8",
    )


def add_rule(rule: LearnedConstraint) -> list[LearnedConstraint]:
    rules = load_rules()
    rules = [r for r in rules if r.id != rule.id]
    rules.append(rule)
    save_rules(rules)
    return rules


def load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        # Seeded "before Askonce" weeks — the chart that wins the room.
        seeded = [
            {"cycle": "Week −5", "overrides": 18, "rules_known": 6},
            {"cycle": "Week −4", "overrides": 16, "rules_known": 6},
            {"cycle": "Week −3", "overrides": 15, "rules_known": 7},
            {"cycle": "Week −2", "overrides": 14, "rules_known": 7},
            {"cycle": "Week −1", "overrides": 13, "rules_known": 8},
        ]
        HISTORY_PATH.write_text(json.dumps(seeded, indent=2), encoding="utf-8")
        return seeded
    return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))


def record_cycle(overrides: int, rules_known: int) -> list[dict]:
    history = load_history()
    history.append(
        {
            "cycle": f"Week {len(history) - 4}",
            "overrides": overrides,
            "rules_known": rules_known,
        }
    )
    HISTORY_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")
    return history


def nurse_map() -> dict:
    return {n.id: n for n in nurses()}
