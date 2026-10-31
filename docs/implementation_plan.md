# Seizure App — Hackathon Implementation Plan

Oct 31, 2026 · @BigP

## Definition of done for the demo

The demo is done when five things work end to end on the real (anonymised) diary, in this order; anything below the line is a slide, not code.

1. **Log a seizure two ways.** A one-tap "just had one" that timestamps instantly and starts a timer, and a voice debrief through Gemini Live that extracts what the carer says and asks one question at a time for what is missing, then reads the record back before saving.
2. **Risk now.** A home tile that says low, medium or high for the next few hours with three plain-word reasons, computed in our own code from the person's own history, with "no data" overnight and "learning your pattern" under 30 events.
3. **Eight years on one screen.** Hour-of-day histogram, monthly bars with medication changes marked, and a scrubber that replays any real day hour by hour through the risk engine.
4. **Trigger lab.** The user names a suspected trigger or symptom; the app tests it on their own log and answers on a ladder from "watching" to "supported", never a flat rejection for lack of data (section 2).
5. **Clinic report.** One page, exported as PDF, in the shape a neurologist expects (section 10).

Below the line (slides only): smartwatch heart rate, multi-carer accounts, dark mode, app-store packaging. Onboarding (section 3) is built only as far as "import this CSV" because the demo diary is the import.

Guardrails that are part of done: the risk tile carries "research prototype, not a prediction"; the emergency card (999/112, 5-minute rule, recovery position) is one tap from every screen; names and the NHS number are redacted before anything reaches Gemini; only the paid Gemini tier is used.

## Trigger lab verdicts: let a real trigger emerge

A binary confirmed / rejected verdict would be wrong most of the time, because most suggested triggers start with almost no data and many genuine ones are weak but real. The fix is a five-rung ladder where "rejected" is reserved for triggers that have had a fair test and failed it, every rung says what would move it, and the app actively helps the user collect the evidence.

| Rung | When | What the user sees | What moves it |
| --- | --- | --- | --- |
| **Watching** | Fewer than 10 exposure days logged | "Logged. I'll flag this each time you note it; 7 more days with hot showers and I can start comparing." | Exposure days accrue (the app asks about this trigger in the daily check-in) |
| **Emerging** | 10+ exposure days, rate ratio above 1.3 but not yet significant (p > 0.05 after correction) | "Seizures are 1.6× more common within 6 h of a hot shower so far, from 14 shower days. Not proven yet; keep logging." | Significance reached (→ Supported) or ratio falls toward 1 (→ Not seen) |
| **Supported** | 10+ exposure days, ratio above 1.3, p < 0.05 after Benjamini–Hochberg, confounder check passed | "In your log, hot showers are followed by more seizures: 2.1× within 6 h, across 31 shower days. Worth discussing with your nurse." | Re-tested monthly; can fall back to Emerging if the effect fades |
| **Not seen so far** | 20+ exposure days, ratio between 0.8 and 1.3 | "No difference in your log yet: 1.0× across 24 days. It might still matter on some days; I'll keep watching." | Stays open; never closes |
| **Unlikely** | 30+ exposure days, ratio below 0.8 or an upper confidence bound below 1.2, confounders checked | "Your log points the other way: fewer seizures after exercise, across 40 days. You can keep logging it or archive it." | User can archive; the test re-runs if they keep logging |

Rules that keep it honest and kind:

- **Lack of data is never a verdict.** Under 10 exposures the only answer is Watching plus a countdown. Under 20 the only negative answer is "not seen so far".
- **Direction before significance.** Emerging exists so that a real trigger with a 1.6× effect and 14 days of data is shown as promising, not dismissed. The honest phrase is "not proven yet", never "rejected".
- **Priors from the literature nudge, they don't decide.** Triggers with evidence (missed dose, sleep-timing shift, menstrual phase, stress, the person's own "feeling off") start one rung higher in wording ("commonly reported; let's see if it holds for you") and get a slightly lower bar (ratio 1.2) for Emerging. Novel triggers ("the smell of the gym") are tested identically but worded as the user's own hypothesis.
- **Symptoms are tested as lead indicators, triggers as exposures.** A symptom ("eyes going funny", "feeling off") is checked for seizures in the next 1 to 6 hours; a trigger (shower, travel, late night) for seizures in the next 6 to 24 hours; a daily factor (stress, sleep) as a day-level rate ratio.
- **Denominator or nothing.** A trigger only counts as exposed on days it was logged as present, and as unexposed on days the check-in was completed and it was absent. Days with no check-in are excluded, not treated as unexposed. The app therefore adds any Watching trigger to the daily check-in automatically.
- **Confounding check, shown in words.** If a trigger coincides with another (showers happen at 19:00, which is already her peak hour), the test is re-run within time-of-day bands and the result says so: "Showers are mostly at 19:00, your riskiest hour; after allowing for that, the effect is 1.3×, still emerging." Rescue medication gets the same treatment (it is given on bad days).
- **Multiple comparisons are corrected across everything tested**, and the number of tests is visible: "12 triggers tested; corrected for that."
- **Every rung has a next step**, and the agent asks for it. Watching: "shall I ask about this at check-in?" Emerging: "keep logging; a verdict needs about 10 more days." Supported: "add to the clinic report?" Unlikely: "archive, or keep watching?"
- **Nothing is deleted.** Archived triggers keep their data and re-open if the user logs them again.

For the demo, pre-run the five triggers the notes support (hot shower or bath, period, travel, exercise, upset) plus one deliberately underpowered one ("after swimming", 4 exposures → Watching) and one that fails fairly ("after screens", 33 notes, ratio 0.7 → Unlikely), so the judges see the whole ladder.

## Onboarding: start fresh or import

Two doors on first launch. "Start fresh" takes under two minutes by voice; "Import what you already have" accepts whatever the family has been keeping, because the people who need this most have years of data in a spreadsheet, a notes app or a paper diary.

### Start fresh (voice, two minutes)

1. Who is this for: me, or someone I care for (name they want used in the app; a role word is enough).
2. Seizure types they have, in their words; the app maps them to the ILAE-style enum and keeps the original wording as the label they see.
3. Current medicines: drug, dose, usual times. Half-life class is looked up from a built-in table so the dose-timing logic works from day one.
4. Rescue plan: rescue medicine if any, who to call, the 5 or 10 minute rule for their seizure type.
5. Anything they already suspect is a trigger or warning sign; each one enters the trigger lab at Watching.
6. Consent screen: what goes to Gemini, which tier, how to delete.

The risk tile then shows "learning your pattern" until 30 events exist; the time-of-day band starts flat.

### Import (any format, mapped by Argon, confirmed by the user)

- Accepts CSV, XLSX (every sheet), an export from Epsy, SeizureTracker or Seer, a Notes app text dump, or photos of a paper diary (Gemini reads the image).
- Argon reads a sample, proposes a column mapping to the contract (date, time, duration, type, severity, notes, rescue med, period flag, dose records), lists its assumptions (date format, day/month order, time zone, what a blank means) and shows a 10-row preview. The user confirms or corrects in one screen.
- Type labels are normalised to the enum with a mapping table the user can edit ("Head strongly to side" → impaired awareness, severe). Free-text notes are kept whole and also tagged by the extractor into `context_tags`, which seeds the trigger lab.
- Dates are sanity-checked: a column where more than half of ambiguous values parse only one way is flagged; the Excel day/month swap in the demo diary would be caught here.
- Gaps are explained, not hidden: "no dose times found; we will start logging them from today"; "no seizure-free days recorded, so trigger tests begin from today's check-ins."
- Names in notes are redacted before upload (local regex plus a confirm list); the NHS number pattern is stripped.
- Import runs the full engine immediately, so a family with eight years of data gets the risk tile, the histogram and pre-run trigger tests on day one. That moment is the demo.

For the hackathon: build the CSV path only, with the demo diary pre-mapped, and show the Argon mapping screen as a mock with the real proposed mapping.

## Architecture

&#91;embedded content: architecture · 8 components, 9 flows\]

The client talks to Gemini Live directly over a WebSocket (ephemeral token from the backend) and to the backend for everything else; tool calls from the Live session and the post-session extractor both land as rows in the store; the engine reads the store and produces every number the user sees; Argon reads the engine's numbers plus the CSV, runs its own exploratory code, and writes the words and the clinic narrative, which flow back to the client through the backend.

## Contract and data model

One contracts package is the handshake between the two of you: JSON Schema in `packages/contracts/schema`, TypeScript and Pydantic generated from it, and a fixture for every endpoint so the UI runs against mocks from the first minute. The full field lists are in the Claude Code kickoff prompt; this is the shape.

| Record | Key fields | Who writes it |
| --- | --- | --- |
| `SeizureEvent` | start\_time, duration\_s (+ estimated flag), type enum, awareness, asleep\_at\_onset, recovered\_at, warning\_before, context\_tags, rescue\_med, who\_logged, confidence, possibly\_non\_epileptic, source (tap, voice, import) | Tap button, voice tools, extractor, importer |
| `Dose` | drug, dose\_mg, scheduled\_time, taken\_time, skipped, reason | Notification tap, voice tool |
| `CheckIn` | date, bed and wake time, sleep quality, stress, mood, fatigue, feeling\_off, unwell, period\_started, alcohol, exercise, big\_event\_tomorrow, plus one yes/no per Watching trigger | Morning voice check-in or form |
| `RiskNow` | tier, score, horizon\_hours, reasons\[\], learning\_mode, overnight\_no\_data | Engine, read-only |
| `TriggerTest` | trigger, kind (symptom, exposure, daily factor), rung, exposure\_days, ratio, ci, p\_adjusted, confounder\_note, next\_step, plain\_text | Engine + Argon wording |
| `ClinicReport` | window, counts by type, severe, convulsive (12 mo), nocturnal (30 d), longest, ≥5 min events, adherence %, rescue doses, medication changes with before/after, triggers by rung, questions, logging-effort note | Engine + Argon narrative |
| `DiaryEntryBatch` | seizures\[\], doses\[\], checkin, open\_questions\[\] | Extractor |

Endpoints (FastAPI, every one with a `?mock=1` path that returns its fixture): `POST /live/token` · `POST /events` · `GET /events` · `POST /doses` · `POST /checkins` · `POST /transcripts/extract` · `GET /risk/now?at=` · `GET /stats/hourly` · `GET /stats/monthly` · `GET /stats/baseline` · `POST /triggers/test` · `GET /triggers` · `GET /report/clinic?window=90` · `POST /analysis/ask` · `POST /import/preview` · `POST /import/commit`.

Rules: contracts change only through a commit that regenerates both sides and updates fixtures; `main` always passes `make demo-check`; the `at` parameter on `/risk/now` exists so the timeline scrubber can replay any hour of the real diary.

## Build timeline

&#91;embedded content: build plan · 3 lanes, 4 phases, 4 gates\]

The highlighted band in each lane is that lane's critical piece. A gate is a thing that must be true before the next phase starts; if a gate slips, the fallback in section 12 applies and the next phase shrinks rather than the demo script changing.

## Risk engine spec

Deterministic Python in `apps/api/engine/risk.py`, run hourly and on every new event, with a unit test that reproduces the backtest. Gemini explains the output; it never produces it.

### Score (points, summed each hour)

| Component | Points | Source of the weight |
| --- | --- | --- |
| Time-of-day band from the person's own hourly histogram (trailing 365 days, min 30 events) | 2 if this hour's share > 2× a flat day, 1 if > 1×, else 0 | Strongest signal in the demo diary (AUC 0.76 alone) |
| Seizures so far today | 0 / 1 / 2 for 0 / 1 / 2+ | 45% → 59% → 69% chance tomorrow |
| Under 6 h since the last seizure | +0.5 | 28% of gaps under 6 h |
| Last 7 days vs trailing 90-day baseline | +1 above 75th percentile, +0.5 above median | 26% vs 61% chance today |
| Scheduled dose overdue by > ¼ of its half-life | +1 | Literature; brivaracetam 9 h, levetiracetam 6 to 8 h, clobazam 10 to 30 h, cenobamate 30 to 76 h |
| Dose skipped today | +2 | Literature |
| `feeling_off` or warning symptom in last 6 h | +2 | OR 3 to 18 in e-diary studies |
| Stress ≥ 7 today | +0.5 only once the person's own trigger test is Emerging or better | Group OR 1.32 per 3 points, real for a minority |

Add once the Samsung import exists: main sleep below the person's own 25th percentile adds 0.5 to the next day's score (in her data, the shortest third of nights were followed by 1.70 seizures against 1.00 after the longest third, rho −0.22, p = 0.008; label it Emerging). Daytime heart rate contributes nothing until the watch is worn in the afternoon.

### Tiers and display

- Thresholds are set per person: over the trailing 90 days, high covers about 15% of hours, low about 50%. Recompute nightly.
- Overnight (00:00 to 07:00, or the person's logged sleep window) returns `overnight_no_data: true` and the tile says "no data while asleep", never "low".
- Under 30 events: `learning_mode: true`; the tile shows only today's count and time since the last seizure.
- Reasons are the top three contributing components in plain words with their numbers ("7 pm is your busiest hour: 11% of your seizures").
- Footer on the tile, always: "A pattern from your own diary, not a prediction. Low never means safe. Research prototype."

### Safety rules, outside the score

- Timer passes 5 min (convulsive) or 10 min (other): emergency screen with the person's plan and a call button.
- Second seizure before `recovered_at` of the first: same.
- Cluster alert: today's count above the person's 90th percentile, or 3 in 24 h, or 2 in 6 h: show the rescue plan and ask whether rescue medication was given.
- Always-visible counters, never blended into the tier: convulsive seizures in the last 12 months, night-time seizures in the last 30 days.

### Tests to ship

- `test_backtest.py`: train ≤ 2023, test 2024 to Aug 2026 on `data/seizures_clean.csv`; assert AUC for "any seizure in next 3 h" ≥ 0.70 and high-tier hit rate ≥ 5× low-tier.
- `test_calibration.py`: high tier occupies 10 to 20% of hours over the trailing 90 days.
- `test_overnight.py` and `test_learning_mode.py`.

## Trigger lab algorithm

`apps/api/engine/triggers.py`. Input: a trigger name, its kind (symptom, exposure, daily factor) and a definition (a context tag, a check-in field, or a free-text keyword list that Flash proposes and the user approves). Output: a `TriggerTest` with the rung from section 2.

1. **Build the exposure series.** Exposure: an hour (symptom), a 6 to 24 h window after the logged event (exposure trigger), or a day (daily factor). Unexposed: hours or days where a check-in or event log exists and the trigger is absent. Days with no check-in at all are excluded. For the imported diary, exposures come from `context_tags` on seizure rows, so the denominator is thin; say so in the output.
2. **Rate ratio.** Seizures per exposed unit over seizures per unexposed unit, with a Wilson or bootstrap 95% interval.
3. **Permutation test.** Shuffle exposure labels within time-of-day band and within month (preserves her evening peak and slow drift), 1,000 shuffles, two-sided p.
4. **Confounders.** Re-run within time-of-day bands; if the ratio drops by more than a third, report both numbers. For rescue medication, compare against days with the same seizure count.
5. **Correction.** Benjamini–Hochberg across every trigger tested for this person; report the number of tests.
6. **Rung.** Apply the ladder: Watching (< 10 exposures), Emerging (ratio > 1.3 or > 1.2 with literature prior, p\_adj > 0.05), Supported (ratio > 1.3, p\_adj < 0.05, confounders passed), Not seen so far (20+ exposures, 0.8 to 1.3), Unlikely (30+ exposures, < 0.8 or upper CI < 1.2).
7. **Wording.** Pass the numbers, the rung and the next step to Argon (or Flash) with a strict template: two sentences, no causal language above "followed by", always a number and a count, always the next step. Store the generated text next to the numbers so it can be audited.
8. **Re-test** nightly and whenever 5 new exposures accrue; rungs move both ways and the history of rungs is kept.

Demo set: pre-compute hot shower or bath, period, travel, exercise, upset (expect Emerging or Supported from the notes), "after swimming" (Watching), "screens" (Unlikely). Cache the results so the screen is instant.

## Voice agent spec

Model `gemini-3.8-live`, audio in and out, both-side transcription with `custom_vocabulary` loaded from the profile (drug names, the person's own seizure words, carer names replaced by roles). Four flat tools, non-blocking; the backend validates every call and writes the row; respond with `scheduling: WHEN_IDLE`.

### System prompt, in order

1. Persona: a calm, brief seizure-diary assistant for a carer or the person themselves; never a clinician.
2. Goal: get one complete record with the least talking. Extract everything the person says first; only then ask.
3. Must-have fields, asked one at a time if missing: start time (accept "about ten minutes ago"), duration or "still going" (start the timer), type in plain words plus whether aware, any warning or aura.
4. Ask-if-not-rushed fields, at most two per entry: what they were doing just before, last dose taken, recovered yet, rescue medicine given, asleep at onset, injury, period.
5. Personal probes from the trigger lab: for every trigger at Watching or Emerging, one direct question when relevant ("was she just in the shower?").
6. Accept vague answers and mark them estimated; never push for precision.
7. Read the record back in one sentence and wait for yes before calling `log_seizure`.
8. Never give dosing or treatment advice; redirect to the epilepsy nurse and offer to note the question for the clinic report.
9. If the timer passes 5 min (convulsive) or 10 min (other), stop and read the emergency plan.
10. Greet first (the API waits for input): "I'm listening. What happened?"

### Tools

- `log_seizure(start_time, duration_s, duration_estimated, type, awareness, warning_before, warning_text, context_tags, rescue_med, recovered, asleep_at_onset, injury, notes, confidence)`
- `log_dose(drug, dose_mg, taken_time, skipped, reason)`
- `log_symptom(text, time)` for "feeling off" and premonitory symptoms outside a seizure
- `get_todays_meds()` so it can ask "did she have the 7 pm cenobamate?" with the right name and time

### Extraction pass

After the session, one `gemini-3.8-flash` call over the full transcript with the `DiaryEntryBatch` schema; reconcile against tool rows (tool row wins on conflict, extractor fills blanks, differences are shown for confirmation). Store the transcript hash with the record.

### Quick path

The "just had one" button never waits for the model: it writes a `SeizureEvent` with `source: tap`, starts the timer, and offers "tell me about it" afterwards, which opens the voice session with the event id so the tools update rather than create.

## Clinic report

One A4 page, counts first, charts second, built from what NICE says a review must cover and what the AAN quality measure requires at every visit: seizure frequency per type, date of last seizure, medication with adherence and side effects, SUDEP-relevant facts, mood. Default window is since the last recorded appointment (else 90 days) with the same-length prior window beside it for comparison. Neurologists estimate 40 to 60% under-reporting and distrust self-classified types, so the report prints its own completeness and never classifies an unwitnessed event.

### Page 1, in order

1. **Header.** Person, report window, generated date, seizure types in ILAE 2017 names with the person's own label in brackets ("focal impaired awareness (head to side, dribbling)"), current medicines. One completeness line: days with any entry out of days in window, share of events logged within 24 h, who logged (self, carer, voice).
2. **Headline row.** Total seizures; seizures per 28 days, this window vs prior, with % change; seizure days; date of last seizure of each type; days since last tonic-clonic (focal-to-bilateral or generalised); longest seizure-free run in the window.
3. **By type (table).** Count, per-28-day rate, median and max duration, % during sleep, % witnessed, clusters (definition stated on the page, e.g. 3 in 24 h), seizures of 5 min or more, prior-window count.
4. **Charts.** Weekly stacked bars by type over 12 weeks with medication-change markers; a 3-month calendar grid with one box per seizure coloured by type (the Epilepsy Society paper diary's "at a glance" layout, which nurses already read).
5. **Medication.** Current drugs, dose and times; changes with dates and the before-and-after rate for each (the "change experiment"); missed doses and adherence % (taken over scheduled); rescue-medicine uses as a log (date, seizure, dose, outcome, 999 called); A&E visits and admissions.
6. **Side effects and wellbeing.** LAEP total (flag 45 or more) with top three items; NDDI-E total (flag over 15; item 4 flagged on its own); GAD-7 band; sleep timing if logged.
7. **Risk factors present**, as NICE lists them, tick or cross, no composite score: tonic-clonic seizures in window; seizures during sleep; lives alone or sleeps unsupervised; missed doses; alcohol; frequency up more than 25% vs prior window. For women: share of seizures in the logged perimenstrual window; pregnancy-planning flag; valproate or topiramate flag.
8. **Trigger lab summary.** Supported and Emerging triggers with their numbers; the count of triggers tested; nothing below Emerging.
9. **The person's top three questions** (free text, drafted by Argon from the window, edited by the user) and the date SUDEP was last discussed.

### Appendix, optional

- Event log: date, time, ILAE type, awake or asleep, duration, witnessed by, context tags, rescue medicine, injury, recovery time, source (tap, voice, import).
- Emergency care plan in the Epilepsy Action S140 / Young Epilepsy individual-healthcare-plan field set: seizure types A/B/C with description, usual duration and warning signs; triggers; call 999 if over 5 min or 2 min longer than usual, repeated without recovery, breathing affected, injury or water; per-type rescue protocol (drug, strength, route, when to give, second-dose rule, max per 24 h, do-not-give conditions); trained people and copy holders; a per-use log; review date.

### Wording rules that clinicians will trust

- ILAE 2017 names only; the person's label beside them. Never "grand mal" or "complex partial".
- Unwitnessed or uncertain events are "unknown onset, possible seizure"; the app never auto-classifies from a voice description without the carer confirming.
- Rates per 28 days, % change vs prior window, date of last seizure per type. No single risk score on the page.
- Print completeness; never present unlogged days as seizure-free.
- "No seizures logged since \[date\]", never "seizure-free" unless 12 months or three times the longest prior interval.
- Facts, not diagnostic labels: "seizure of 6 min; 999 called", not "status epilepticus".
- State the cluster definition on the page.
- Page 1 is readable in under a minute; everything else is appendix.

Sources: [NICE NG217](https://nice.org.uk/guidance/ng217/resources/epilepsies-in-children-young-people-and-adults-pdf-66143780239813) · [NICE QS211 care plan](https://www.nice.org.uk/guidance/QS211/chapter/quality-statements) · [NICE IND227 annual review](https://www.nice.org.uk/indicators/ind227-epilepsy-annual-review/IND227.pdf) · [ILAE 2017 classification](https://webdav.lcsb.uni.lu/public/pc1811/Fisher_et_al-2017-Epilepsia.pdf) · [AAN quality measures](https://www.aan.com/practice/epilepsy-seizures-quality-measures) · [Fisher 2012 diary paper](https://scholar.barrowneuro.org/neurology/547) · [NINDS CDEs](https://www.commondataelements.ninds.nih.gov/sites/nindscde/files//Doc/EPI/CDEStartupResource_Epilepsy.pdf) · [Epilepsy Action appointment checklist](https://www.epilepsy.org.uk/living/10-ways-to-prepare-for-appointments) · [Epilepsy Society diary](https://epilepsysociety.org.uk/sites/default/files/2025-12/SeizurediaryA4Sept2025editable.pdf) · [Epilepsy Action emergency care plan](https://www.epilepsy.org.uk/app/uploads/2024/04/S140_-_EMERGENCY_MEDICATION_CARE_PLAN-Final.pdf) · [Young Epilepsy IHP](https://www.youngepilepsy.org.uk/sites/default/files/2023-10/IHPform.pdf) · [SUDEP Action checklist](https://sudep.org/checklist) · [neurologists' views on diaries](https://www.intechopen.com/chapters/56714) · [NDDI-E](https://dgfe.org/fileadmin/user_upload/wegweiser/NDDI-E.pdf) · [GAD-7](https://www.corc.uk.net/outcome-experience-measures/generalised-anxiety-disorder-assessment-gad-7/) · [LAEP](https://www.epistemonikos.org/pt/documents/90128657aa2f94a4e60a086db7763bd33f19f95d)

## Demo script (four minutes)

1. **0:00 The problem, one slide.** "Half of seizures go unrecorded, triggers are guesses nobody tests, and families log for years and get nothing back. This family logged 2,600 seizures over eight years, then stopped writing notes."
2. **0:30 Import.** Drop the CSV; the mapping screen shows Argon's proposed columns and one flagged assumption (the Excel day/month swap). Confirm. The home screen fills: risk tile, today's strip, eight years of history.
3. **1:00 Log one.** Tap "just had one"; timer runs. Tap again, say: "She had one about quarter past seven, maybe a minute and a half, her head went to the side, she'd just got out of the shower." The record fills in live; Gemini asks one thing: "Had she taken her 7 pm cenobamate yet?" Answer "not yet". Read-back, yes, saved. The risk tile moves to high with three reasons: busiest hour, second seizure today, evening dose not yet logged.
4. **1:45 Eight years in eight seconds.** Timeline screen: hour-of-day histogram ("75% between midday and 10 pm, peak at 7 pm"), monthly bars with medication changes. Scrub the day of 29 Jan 2019 hour by hour and watch the tile climb.
5. **2:15 The change experiment.** Open the September 2025 brivaracetam re-timing: 5.4 to 10.5 a week, afternoon-and-evening seizures up 1.67×, mornings down. Then the March 2025 cenobamate cut: "within her usual range". Same feature, opposite answers, both right. "This is evidence for her neurologist, not advice."
6. **2:45 Trigger lab.** Show the ladder: hot showers Supported (2.1×, 31 days), period Emerging, swimming Watching with a countdown, screens Unlikely. Type a new one: "after the train". Argon runs it live: Emerging, 1.6×, 14 days, "keep logging".
7. **3:20 Clinic report.** Export the one-page PDF: counts by type, convulsive and night-time counters, dose adherence, the two medication changes with before/after, triggers by rung, three questions for the clinic.
8. **3:45 Honest close.** "Risk is hours-ahead and explained, never a forecast; we analyse witnessed seizures; this is a research prototype. Built on `gemini-3.8-live` for voice and `gemini-4-argon` for analysis."

Record a backup video of step 3 before the demo; keep the fixtures hot so every other screen renders with Wi-Fi off.

## Risks and fallbacks

| Risk | Likelihood | Fallback |
| --- | --- | --- |
| Venue Wi-Fi blocks or drops the Live WebSocket | High | Pre-recorded video of the voice debrief; the extractor path (`POST /transcripts/extract` on a typed transcript) still demos the structured record live |
| Argon billing not enabled on the key | Medium | `gemini-3.8-flash` runs the same code; swap the model string in one env var |
| Browser mic permissions or audio worklet glitches on the demo laptop | Medium | Test on the exact laptop and browser an hour before; keep a second laptop with the repo pulled |
| Live session hits the 10-minute connection limit mid-demo | Low | `session_resumption` is on; the UI reconnects silently |
| Transcription mangles drug names | Medium | `custom_vocabulary` with every drug in the profile; the read-back step catches the rest |
| Trigger lab results look thin on the imported diary (no denominator days) | High | The output says so in words; pair every result with the countdown to a better verdict; show one Supported result that the notes genuinely back |
| Running out of time | High | The build order is strictly demo-able at every step: stop at step 4 (trigger lab) and the report becomes a slide |
| Someone types a real name into the voice session | Medium | Redaction runs on the transcript before extraction and before storage |
| A judge asks "is this legal?" | Certain | "The diary and report are not a device; the risk level would be on release, so it ships as pattern insights for the clinician; the demo is a research prototype on anonymised data." |

## Recommendation: what to build where

One-shot the repo in Claude Code with the kickoff prompt, and have this session build the engine package in parallel. The two jobs need different things: the repo needs a shell, two dev servers, git and a browser to iterate against; the engine needs the data and the numbers, which are already here.

| Piece | Build it with | Why |
| --- | --- | --- |
| Repo scaffold, `.claude` setup, contracts, fixtures, `make dev`, both apps | Claude Code, one session per person after the scaffold | Multi-process, multi-file, long-running; needs to run servers and open a browser |
| `engine/` package: `risk.py`, `triggers.py`, `stats.py`, `report_data.py`, `importer.py`, tests, and the fixture JSON generated from the real diary | This session, now | Self-contained Python over a CSV; the analysis and backtest already exist here; delivered as a zip you drop into `apps/api/engine` |
| Voice client and Live session | Claude Code (UI side, from Google's example) | Needs mic, audio worklet, real browser testing |
| Argon analysis and trigger wording | Claude Code (backend side) once the engine is in | Needs the API key and a running backend |
| Clinic report PDF | Claude Code (backend) from `report_data.py` | Templating and rendering |

### Split between the two of you

- **Backend person:** start Claude Code with the kickoff prompt; it scaffolds everything and gets `make dev` up. Then drop in the engine zip, wire the endpoints to it, replace fixtures with engine output, then the Live token endpoint and tools, then Argon.
- **UI person:** once the scaffold exists (about 20 minutes), open a second Claude Code session in `apps/web` with `/ui`. Build Home and Timeline against fixtures, then the voice screen from the Google example, then Trigger lab and Report. Never wait on the backend; flip from mock to live by env flag when each endpoint turns green.
- **You, in between:** keep `PROGRESS.md` honest, run `make demo-check` before every merge, record the backup video as soon as the voice path works once.

### First hour

- T+0: backend person pastes the kickoff prompt; this session starts the engine package.
- T+20: scaffold is up with fixtures; UI person starts.
- T+40: engine zip lands; backend wires `/risk/now`, `/stats/*`, `/triggers`, `/report/clinic` to it; fixtures regenerate from real data.
- T+60: Home and Timeline render real numbers; voice work begins on both sides.

Say the word and the engine package starts here.
