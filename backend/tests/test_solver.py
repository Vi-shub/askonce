from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.models import Infeasibility
from app.seed import nurses
from app.solver import solve
from app.store import save_rules


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
    assert client.get("/api/health").json()["ok"] is True
