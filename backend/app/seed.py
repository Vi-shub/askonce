from __future__ import annotations

from datetime import date, timedelta

from app.models import Nurse

# Two-week horizon. Day 0 is Monday 6 Oct 2026.
PERIOD_START = date(2026, 10, 6)
NUM_DAYS = 14
SHIFTS = ("day", "evening", "night")

# 12 nurses on the floor → 4 / 3 / 3 coverage, two off each day.
COVERAGE = {"day": 4, "evening": 3, "night": 3}
MAX_NIGHTS = 6  # 14 nights × 1 charge; 3 charges × 6 = 18
MAX_SHIFTS = 12  # 10 staffed slots/day × 14 days = 140; 12×12 = 144 capacity
NO_NIGHT_THEN_DAY = True


def period_dates() -> list[date]:
    return [PERIOD_START + timedelta(days=i) for i in range(NUM_DAYS)]


def weekday_name(day_index: int) -> str:
    return period_dates()[day_index].strftime("%a")


def first_index_for_weekday(weekday: int) -> int:
    for i, d in enumerate(period_dates()):
        if d.weekday() == weekday:
            return i
    return weekday


def nurses() -> list[Nurse]:
    return [
        Nurse(
            id="n01",
            name="Kenji Tanaka",
            role="charge",
            notes="Charge; often covers nights. High callout load last quarter.",
            prior_callouts=4,
            prior_nights=18,
            prior_weekends=8,
        ),
        Nurse(
            id="n02",
            name="Mei Lin",
            role="charge",
            notes="Charge. Prefers days. Mentors juniors.",
            prior_callouts=1,
            prior_nights=9,
            prior_weekends=5,
        ),
        Nurse(
            id="n03",
            name="Aiko Yamada",
            role="rn",
            legal_flags=["postpartum_no_nights"],
            notes="Labour Standards: no night work (22:00–05:00) while nursing. Hard legal.",
            prior_callouts=0,
            prior_nights=0,
            prior_weekends=3,
        ),
        Nurse(
            id="n04",
            name="Priya Sharma",
            role="rn",
            notes="Strong RN. Unwritten: family dinner every Saturday — not in the system yet.",
            prior_callouts=2,
            prior_nights=11,
            prior_weekends=6,
        ),
        Nurse(
            id="n05",
            name="Hana Kim",
            role="rn",
            notes="Weekend-heavy last roster. Fairness ledger is watching.",
            prior_callouts=3,
            prior_nights=12,
            prior_weekends=9,
        ),
        Nurse(
            id="n06",
            name="Daniel Tan",
            role="rn",
            notes="Reliable nights. Already absorbed extra callouts.",
            prior_callouts=5,
            prior_nights=16,
            prior_weekends=7,
        ),
        Nurse(
            id="n07",
            name="Siti Rahim",
            role="rn",
            notes="New to nights; competent.",
            prior_callouts=1,
            prior_nights=6,
            prior_weekends=4,
        ),
        Nurse(
            id="n08",
            name="Yuto Sato",
            role="junior",
            notes="Junior. Cannot be sole night cover.",
            prior_callouts=0,
            prior_nights=4,
            prior_weekends=2,
        ),
        Nurse(
            id="n09",
            name="Grace Ong",
            role="junior",
            notes="Junior, study nights on weekdays.",
            prior_callouts=1,
            prior_nights=3,
            prior_weekends=3,
        ),
        Nurse(
            id="n10",
            name="Ravi Menon",
            role="rn",
            notes="Even keel. Low penalty score.",
            prior_callouts=0,
            prior_nights=8,
            prior_weekends=4,
        ),
        Nurse(
            id="n11",
            name="Lina Park",
            role="charge",
            notes="Third charge. Split across days/evenings.",
            prior_callouts=2,
            prior_nights=10,
            prior_weekends=5,
        ),
        Nurse(
            id="n12",
            name="Farah Aziz",
            role="rn",
            notes="Requests fewer consecutive nights.",
            prior_callouts=1,
            prior_nights=7,
            prior_weekends=4,
        ),
    ]


WARD = {
    "id": "ward-4e",
    "name": "Ward 4 East",
    "hospital": "Harbor General (JAPAC demo)",
    "policy": [
        "At least one charge nurse on every night shift.",
        "No night → day (insufficient rest).",
        "Max 6 nights in the 14-day period.",
        "Max 12 shifts in the 14-day period (hours cap stand-in).",
        "Postpartum / nursing: no nights (Japan Labour Standards analogue).",
        "Fairness: unsociable shifts and callouts spread using a running penalty ledger.",
    ],
}
