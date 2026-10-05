from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.models import Infeasibility
from app.seed import first_index_for_weekday, nurses
from app.solver import solve
from app.store import load_rules, save_rules


def setup_function():
    save_rules([])


def test_solver_covers_nights_with_charge():
    roster = solve([])
    assert not isinstance(roster, Infeasibility), getattr(roster, "summary", roster)
    assert roster.status in ("optimal", "feasible")
    by_day = {}
    for a in roster.assignments:
        by_day.setdefault((a.day_index, a.shift), []).append(a.nurse_id)
    staff = {n.id: n for n in nurses()}
    for d in range(14):
        nights = by_day.get((d, "night"), [])
        assert len(nights) == 3
        assert any(staff[i].role == "charge" for i in nights)
        assert "n03" not in nights


def test_yamada_night_pin_is_infeasible():
    result = solve([], locks=[("n03", 0, "night")])
    assert isinstance(result, Infeasibility)


def test_health():
    client = TestClient(app)
    body = client.get("/api/health").json()
    assert body["ok"] is True


def test_demo_setup_places_priya_saturday_night():
    client = TestClient(app)
    res = client.post("/api/demo/setup").json()
    assert res["ok"] is True
    sat = first_index_for_weekday(5)
    cell = next(
        a
        for a in res["roster"]["assignments"]
        if a["nurse_id"] == "n04" and a["day_index"] == sat
    )
    assert cell["shift"] == "night"


def test_priya_override_blocks_both_saturdays():
    client = TestClient(app)
    setup = client.post("/api/demo/setup").json()
    sat = first_index_for_weekday(5)
    ov = {
        "nurse_id": "n04",
        "day_index": sat,
        "from_shift": "night",
        "to_shift": "off",
        "manager": "Nurse Manager Sato",
    }
    proposed = client.post("/api/override/propose", json=ov).json()
    assert proposed["unexplained"] is True
    confirmed = client.post(
        "/api/override/confirm",
        json={
            "override": ov,
            "option_id": "permanent_weekday",
            "free_text": "family dinner every Saturday",
        },
    ).json()
    assert confirmed["ok"] is True
    rules = load_rules()
    assert len(rules) == 1
    assert "Saturday" in rules[0].reason or "family" in rules[0].reason.lower()
    sat2 = sat + 7
    for day in (sat, sat2):
        cell = next(
            a
            for a in confirmed["roster"]["assignments"]
            if a["nurse_id"] == "n04" and a["day_index"] == day
        )
        assert cell["shift"] != "night"


def test_force_yamada_endpoint():
    client = TestClient(app)
    res = client.post("/api/force", json={"nurse_id": "n03", "day_index": 0, "shift": "night"})
    body = res.json()
    assert body["ok"] is False
    assert "infeasible" in body
