# SAKSHYA — 2-minute demo script

## Before you start

```bash
cd backend && .venv/Scripts/python -m app.db.seed
```

Re-seeding is safe and idempotent. To reset to a *pristine* demo state
(recommended right before judging), delete the database first:

```bash
cd backend && rm -f sakshya.db && .venv/Scripts/python -m app.db.seed
```

Start both servers, open <http://localhost:5173>, and **log out** so you begin
on the login screen. The login page has one-click demo buttons — never type
credentials during the demo.

---

## The 15 seconds that matter

If you only get one point across, make it this one:

> **Non-Response Analysis** shows a mastery of **0.95** — the highest number on
> the board — and SAKSHYA still refuses to assign a level. The learner scored
> 95% on the course. That is not proof they can do it.

Everything else in the demo supports that claim.

---

## Script

**[0:00] Log in as Learner** — click the *Learner* demo button.

**[0:10] The competency profile.** Six competencies for a Junior Statistical
Officer. Three meet target, three do not.

> "Every level here was recalculated from evidence when this page loaded.
> Nothing is stored as a score."

**[0:20] The top-priority card.** Point at it — it names the most severe gap and
why it is the most severe.

**[0:30] The money shot.** Scroll to *Non-Response Analysis & Adjustment*.
Status: **Insufficient evidence**. Click **"Why this level?"**

> "Mastery 0.95 from one course completion. Course completion is weighted 0.4
> against a simulation's 1.5, so the effective evidence is 0.37 — below the 1.5
> threshold. So the system says: I don't know yet."

Point at the contribution table: score, type weight, recency, share.

**[0:50] Close the loop.** Go to **My pathway**. Non-Response is the top gap.
Note the stage chip: **Practice**, not Learn.

> "It doesn't send them back to the course. They've already read it. The
> evidence is passive, so the next step is to do the work."

**[1:05] Run the simulation.** Click through to *Rising non-response in a
household survey*. Answer the four decisions — pick the sensible options
(compare respondents, weighting classes, collapse the small class, state the
assumption).

**[1:25] Submit.** The result page shows the deterministic score, the
decision-by-decision rubric feedback, and:

> "Evidence recorded."

**[1:35] Back to the profile.** Non-Response has moved from *Insufficient
evidence* to an asserted level. Confidence has risen.

> "New evidence, recalculated competency. That's the whole loop."

**[1:45] Log in as SME.** Click the *Subject Matter Expert* button. The review
queue shows generated questions, each with its source citation and a
**✓ Grounded** badge.

> "Every question is checked against the passage it cites — both that the quote
> is really there, and that the answer marked correct is supported by it.
> Nothing reaches a learner without a human approving it."

Point at the **rejected** item — drawn from the document's front matter, with
the reviewer's reason visible.

**[2:00] Done.**

---

## If you have 30 more seconds

- **Admin** login → organisation view: which competency is the biggest training
  need across the cohort, and how many learners are *unproven* rather than just
  low-scoring.
- **Evidence ledger** → *Export CSV*: the full audit trail, every row flagged as
  prototype data.
- `GET /api/v1/competency-method` → the scoring constants are published as data,
  so any result can be recomputed by hand.

---

## Questions judges are likely to ask

**"Is the AI deciding the competency score?"**
No. Scoring lives in `app/engines/` as pure deterministic functions. AI is
confined to `app/ai/` and never feeds them. The simulation debrief is generated
*after* scoring finishes and cannot alter it.

**"Could the AI invent a citation?"**
Structurally, no. The generator is extractive — it never writes prose of its
own. Every draft is then verified against the stored chunk it cites, and
failures are flagged rather than published.

**"Is this connected to iGOT Karmayogi?"**
No, and we haven't pretended otherwise. `LearningCatalogAdapter` is the
integration boundary; the shipped implementation is a local prototype catalogue
with `is_live_integration = False`.

**"Is this real government data?"**
No. Every seeded record carries `is_prototype_data`, the UI shows a persistent
prototype banner, and the sample document states inside itself that it is
synthetic material written for this prototype.

**"Does it run on PostgreSQL?"**
The models are driver-agnostic and there's a pgvector adapter behind the
`VectorStore` interface, but it has not been executed — the build machine has no
Docker. That's labelled in the code rather than glossed over.
