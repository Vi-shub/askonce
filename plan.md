# Askonce — build plan

**Pitch (every slide, every video second 0):**  
Askonce — the roster that learns the rules nobody wrote down.

**Contest:** AI Builder Cup 2026 · Theme: Future of Work & Enterprise Productivity  
**Today:** 5 Oct 2026  
**Team lock:** 11 Oct 2026  
**Submit:** 18 Oct 2026  
**Finale (if shortlisted):** 4 Dec 2026, Singapore

Do not pitch “AI scheduling.” UKG already schedules. The product is: **one question, then the rule exists forever.**

---

## 1. What winning looks like

Judges score:

| Criterion | Weight | How Askonce earns it |
|---|---|---|
| Technical merit & Gen AI | 40% | Gemini types a constraint with provenance; CP-SAT proves it; `INFEASIBLE` becomes two legal choices |
| Problem alignment & impact | 25% | Night callouts, fairness ledger, hours/night-work flags. Local ward, global pattern |
| Innovation | 25% | Override is the training signal — configuration drift dies |
| UX | 10% | Desk grid + phone ping, side by side, no extra explanation |

**The demo’s main event (non-negotiable):**  
Manager takes someone off a shift → *that broke none of my rules, so I’m missing one* → one question → rule saved with name and date → roster updates.

If the main event is “a pretty 14-day grid,” we lose.

---

## 2. Already built (as of 5 Oct)

Working prototype in this folder. Desk + phone + side-by-side. Same API.

- 12 nurses, 14 days, Google OR-Tools CP-SAT
- Coverage, rest (no night→day), charge-on-nights, hours cap, postpartum night ban
- Override → missing-rule modal → confirm → re-solve
- 23:10 callout with fairness pick + draft message
- Illegal pin (Yamada on nights) refused in English
- Seeded “overrides falling” chart
- Optional Gemini; heuristic path works without a key
- PWA (`/#phone`) — that is the phone app for submission

**Run**

```bash
# terminal 1
cd askonce/backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000

# terminal 2
cd askonce/frontend
npm run dev
```

Open http://localhost:5173

---

## 3. Out of scope (do not start)

Payroll, HRIS, 12 industries, App Store / Play Store, React Native, a second roster grid on mobile, Slack/WhatsApp real send, real hospital SSO, 28-day / 24-nurse expansion until the loop is boringly solid.

---

## 4. Calendar (5 Oct → 18 Oct)

### 5–6 Oct — lock the loop

- [x] Demo setup pins Priya on Saturday night (Start demo)
- [x] Callout lights the phone in **Side by side** (default layout)
- [x] Yamada refuse is human, not `INFEASIBLE`
- [ ] Put `GEMINI_API_KEY` in `backend/.env`
- [ ] **Second teammate named and registered by 11 Oct**

### 7–8 Oct — Gemini must be visible

- [x] Override question uses Gemini structured JSON when a key is present
- [x] Infeasibility summary from Gemini
- [x] Voice box parses into the same modal
- [x] Provenance on every rule: who, when, which override
- [x] “Why Gemini” note in README

### 9–10 Oct — deploy (required)

- [x] One Cloud Run image (API + UI) — `Dockerfile` + `deploy.md`
- [ ] `gcloud run deploy` with a real project (needs your GCP account)
- [x] Secret is env/Secret Manager, not Git
- [ ] Paste live URL into README after deploy
- [ ] Public GitHub repo

### 11 Oct — team formation deadline

- [ ] Team of 2–4 on Hack2skill. Solo is not allowed at submit.
- [ ] Everyone 21+, JAPAC, no students (contest rule).

### 12–13 Oct — demo tape

- [ ] Script below, timed under **2:50**
- [ ] Record **Side by side** as the only layout
- [ ] One take with no voice-over explaining “configuration drift” until *after* the drag
- [ ] Upload unlisted YouTube / Drive

### 14–15 Oct — deck (PDF)

10 slides max:

1. Title + pitch line  
2. The bad schedule (one true story: 23:10, same three people)  
3. Why software gets abandoned (rules in the manager’s head)  
4. Product: ask once  
5. Live still: missing-rule modal  
6. Architecture: Gemini → typed rule → CP-SAT → Cloud Run  
7. Desk vs phone (two jobs, one backend)  
8. Chart: overrides down, rules known up  
9. Impact (hours saved, fairness, legal refuse)  
10. What’s next (one packet type: nursing; then factories)

### 16–17 Oct — harden and cut

- [ ] Seed 3 scripted stories only: Priya, callout, Yamada  
- [ ] Empty states, one error toast, no dead buttons  
- [ ] README matches the live URL  
- [ ] Sleep

### 18 Oct — submit

- [ ] Deployed URL  
- [ ] Public GitHub  
- [ ] Video < 3 min  
- [ ] Deck PDF  
- [ ] Theme: Future of Work  
- [ ] English everything  

---

## 5. Three-minute video script

**0:00–0:12** Title. “Askonce. The roster that learns the rules nobody wrote down.”  
**0:12–0:25** Ward 4 East. Generate. Grid fills.  
**0:25–0:55** Priya off Saturday. Modal: *that broke none of my rules.* Permanent. Type `family dinner every Saturday`. Re-solve. Point at the empty Saturday.  
**0:55–1:25** Rule memory: who taught it, when. “We asked once.”  
**1:25–2:05** 23:10 callout. Phone pulses. Fairness reason. *I can cover.*  
**2:05–2:30** Force Yamada onto nights. Two legal choices. No `INFEASIBLE`.  
**2:30–2:50** Overrides chart falling. “The unwritten rules are now the system.” End card: URL + GitHub.

---

## 6. Risks

| Risk | Tell | Fix |
|---|---|---|
| Looks like a scheduler | Grid is the hero | Modal is the hero; grid is the before/after |
| Gemini unused | Heuristic-only demo | Key in `.env` by 7 Oct; voice parse on camera |
| No live URL | Ineligible | Cloud Run 9–10 Oct, even if ugly |
| Scope creep | Native apps, payroll | Close this file and say no |
| Team late | Disqualified 11 Oct | Register humans this week |
| Dry talk | “Configuration drift” first | Drag first, name it after |

---

## 7. Owners (fill names)

| Work | Who |
|---|---|
| Solver / API | |
| UI / demo recording | |
| Gemini prompts + eval | |
| Cloud Run / Firebase | |
| Deck + video voice | |

---

## 8. Definition of done for 18 Oct

A stranger can open the live URL, generate, take Priya off Saturday, teach one rule, see the next Saturday empty, fire 23:10, see the phone, fail Yamada, and understand the product without you in the room.
