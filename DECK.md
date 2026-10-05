# Askonce — deck (convert to PDF)

Keep to 10 slides. One idea per slide. No architecture wallpaper.

## 1. Title
**Askonce**  
The roster that learns the rules nobody wrote down.  
AI Builder Cup 2026 · Future of Work · Gemini + OR-Tools CP-SAT + Cloud Run

## 2. The 23:10 problem
A nurse calls in sick. The manager already knows who will say yes: the same three people who always say yes. Scheduling software posted a legal grid. It did not know the house rules. It did not know who already covered last week.

## 3. Why the software gets abandoned
Implementation captures rules someone can say in a meeting. The real rules live in the manager’s hand: a drag off Saturday night. Every unmatched rule becomes a manual override. After one bad roster, they check every line. The licence keeps renewing.

## 4. Product
Askonce treats the override as a missing constraint.  
**One question. Then the rule exists.**  
Not a chatbot on a timetable.

## 5. The loop (screenshot)
Manager takes Priya off Saturday night.  
Modal: *That broke none of my rules.*  
Permanent. `family dinner every Saturday.`  
Re-solve. Both Saturdays empty. Provenance: who, when, from which override.

## 6. How it is built
Gemini (structured JSON) writes the rule in English.  
Google OR-Tools CP-SAT proves a legal roster — or a human refusal, never `INFEASIBLE`.  
Desk = learn. Phone = 23:10 yes/no. One Cloud Run service.

## 7. Two surfaces, one backend
**Desk:** 14-day ward, drag is the training signal, fairness chart.  
**Phone:** incoming cover request + teach a rule from the floor.  
PWA on `/#phone`. Side-by-side for the demo.

## 8. Proof
Overrides-per-week chart falling. Rules-known rising.  
That is configuration drift dying in public.

## 9. Impact
Hours not spent rebuilding the grid. Unsociable shifts spread by a ledger, not guilt. Illegal assignments refused in English (postpartum night ban). One ward now; the same loop is any shift-based floor.

## 10. Next
Keep the loop. Then factories, then retail close. Same question: *why did you move that person?*
