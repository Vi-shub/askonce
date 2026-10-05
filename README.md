# Askonce

**The roster that learns the rules nobody wrote down.**

AI Builder Cup 2026 · Future of Work & Enterprise Productivity  
Google stack: Gemini (structured output) + OR-Tools CP-SAT + one Cloud Run service.

Do not pitch this as “AI scheduling.” UKG already schedules. Askonce treats every manager override as a missing constraint, asks **one** question, writes a hard rule with provenance, and re-solves.

## Why Gemini

Gemini does not draw the grid. CP-SAT does. Gemini’s job is the part a solver cannot do: turn a messy human override (“family dinner every Saturday”) into a typed rule with a question a manager will actually answer. With a key, that uses JSON schema. Without a key, a heuristic still completes the demo.

## Run locally (two processes)

```bash
cd askonce/backend
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# put GEMINI_API_KEY in .env when you have one
uvicorn app.main:app --reload --port 8000
```

```bash
cd askonce/frontend
npm install
npm run dev
```

Open http://localhost:5173 — it opens **Side by side**. Click **Start demo**.

## Run as one process (what you deploy)

```bash
cd askonce/frontend && npm run build
cd ../backend
.\.venv\Scripts\uvicorn app.main:app --port 8080
```

Open http://127.0.0.1:8080

Cloud Run: see `deploy.md`. Deck: `DECK.md`. Day plan: `plan.md`.

## Demo (3 minutes)

1. **Start demo** — Priya is on Saturday night on purpose.
2. **Demo: Priya off Saturday** — *that broke none of my rules.*
3. Keep **Permanent**, keep `family dinner every Saturday`, **Teach Askonce**.
4. Both Saturdays empty; rule memory shows who taught it.
5. **23:10 callout** — the phone pulses; tap **I can cover**.
6. **Force Yamada onto nights** — refused in English.

## Scope

**In:** override → one question → CP-SAT → callout → legal refusal → override chart.  
**Out:** payroll, App Store, a second native app.
