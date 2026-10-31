# HANDOFF — seizure diary hackathon app

Written 31 Oct 2026, 13:55, by the session that built the walking skeleton. Read this once, then CLAUDE.md for the
rules and PROGRESS.md for live status. This file explains **what exists, why it is shaped this way, how each part works,
what is proven, what is not, and what to do next on the backend.**

---

## 0. The product in three sentences

A voice-first seizure diary for people with frequent seizures and their carers. The home screen shows **risk over the
next few hours (low / medium / high)** computed deterministically from the person's own history, with its reasons; a
**trigger lab** tests any suspected trigger on their own log and places it on a five-rung ladder that never rejects for
lack of data; a **one-page clinic report** comes out in the shape NICE/AAN and epilepsy nurses expect. Gemini Live
captures seizures by voice and asks one question at a time for what is missing; Gemini 4 Argon explains numbers, answers
free-text questions over the diary with code execution, and drafts narrative. **Gemini never produces a number the user
acts on; the engine does.**

## 1. The data we built on (facts you can quote)

- Family diary, `apps/api/data/family_diary.xlsx`, tab "Seizure Data": 2,598 dated seizures, 25 Jul 2018 → 24 Aug 2026,
  with clock time (2,551), duration, a free-text type label (~10 recurring phrases), severity H/L (791 H), clobazam
  rescue doses (188), period flag (11 days), 786 notes. Names and an NHS number exist in the source; the importer redacts
  names → role words (`engine/importer.py:redact`) and never reads the NHS header.
- Medication timeline, `apps/api/data/medication_timeline.csv`: 46 dated regimen changes, hand-checked. **Excel swapped
  day and month** on every date it could in the original chart (stored month = typed day). The three 2025 brivaracetam
  changes are **1, 6 and 10 September 2025**, not Jan/Jun/Oct.
- Headline analysis (all reproduced by the engine/tests):
  - 0.88 seizures/day overall; 55% of days have ≥1; 7% of days have 3+. Since Sep 2025: 42.6 per 30 days, 78% of days.
  - **Time of day dominates**: 75% of seizures start 12:00–22:00, peak 19:00 (the 19:00 hour alone holds 15% of all
    severe ones). The 14:00–22:00 share grew from 52% (2019–21) to 78% (2024–26). Only 4% overnight (under-observed).
  - Sep 2025 brivaracetam re-timing (14:00 dose removed): 5.4 → 10.5/week in 8 weeks (p=0.0003); seizures after 15:00
    ×1.67 over the following year; mornings ×0.86; severe seizures barely moved. Confounded by drama-school term starting
    the same day. Strongest medication signal in the diary; the "change experiment" demo.
  - Clustering: P(seizure tomorrow) 45% after a zero day → 73% after 3+. Last-7-day count 0–1 → 26% chance today; 7+ →
    61%. Severe-tomorrow is flat (~22%) regardless. Within a day, median gap 3.4 h; 28% of gaps < 6 h.
  - Day of week weak (p=0.04); multidien cycle faint (~7.5 d at the 95% permutation line only); menstrual: no pattern
    in the diary's 11 flags, in 6 clean Samsung-flow cycles, or in 8 cycles in another analysis.
  - Notes mining (severe share, 38% overall): heat/shower/bath 56% (n=93), period 63% (n=38), travel 56% (n=46), exercise
    48% (n=127), upset 45% (n=67); "felt it coming" notes 18% (aborted events).
  - Hour-level backtest (train ≤2023, test 2024–Aug 2026), awake hours only, "any seizure in next 3 h": the engine's score
    reaches **AUC 0.69**, high tier (17% of hours) hits 29% vs low tier (45% of hours) 8%, ratio 3.5. A day-ahead forecast
    is ~AUC 0.54 — not a product. The 0.76 figure in the research brief included overnight hours; don't compare them.
- Samsung Health export (analysed, **not imported into the app yet**): the watch was worn at night (82–87% coverage 00–08h)
  and barely in the day (9–30% 12–21h), so daytime HR is useless for her. Sleep length predicts next-day count (rho −0.22,
  p=0.008, 137 nights: shortest third → 1.70 next day, longest third → 1.00). 1,075 walks: 2.2× seizure rate in the 2 h
  after vs matched hours (confounded by "out and active"). 32 night-time HR surges on 138 nights, none near a logged
  seizure. Scripts and CSVs are in the research pack, not in this repo.

Research briefs with sources (Claude docs, shared with the team): "Seizure Tracking App — Research & Data Analysis
Brief" and "Seizure App — Hackathon Implementation Plan". Everything numeric above is in them with charts.

## 2. Architecture and why

```
apps/web (React+Vite PWA) ──HTTP /api──▶ apps/api (FastAPI)
      │                                    ├── app/        routes, service (engine over store, cached), store (SQLite), config
      │ WebSocket (ephemeral token)        ├── engine/     PURE: risk, triggers, stats, report, importer, backtest
      ▼                                    └── gemini/     ONLY code that talks to Google; every function has a mock
 Gemini Live ──tool calls──▶ browser ──POST /live/tool──▶ gemini/tools.py ──▶ store
packages/contracts: JSON Schema → Pydantic (py/contracts) + TypeScript (ts/) + fixtures/*.json (from real data)
```

Decisions you should not re-litigate (each was deliberate):

1. **Contracts are the single source of truth.** `packages/contracts/schema/contracts.schema.json` → `make contracts`
   regenerates both languages. Rows in SQLite keep the full contract JSON in a `payload` column plus a few indexed columns,
   so the DB can never drift from the contract and migrations are trivial (add a field to the schema; old rows validate
   with defaults).
2. **Engine is pure and DataFrame-based.** `EngineData.from_models(...)` builds canonical DataFrames once; every engine
   function takes `EngineData` and returns contract models. No I/O, no globals, deterministic (seeded RNGs). This is what
   makes the backtest a unit test and the numbers auditable.
3. **All timestamps are timezone-aware** (Pydantic `AwareDatetime`). Local zone is `Europe/London` (`APP_TIMEZONE`).
   Diary times are localised on import; the API accepts naive ISO strings in `?at=` and localises them.
4. **Mock-first API.** Every read endpoint serves `packages/contracts/fixtures/<name>.json` when `?mock=1`; fixtures are
   generated from the real diary by `scripts/seed.py`, so "mock" means real numbers, frozen. The web app flips with
   `VITE_USE_MOCK=1`.
5. **Gemini behind one module with mocks.** No key → `gemini.client.get_client()` returns `None` and every function returns
   a labelled mock (`mock: true`). The demo cannot be broken by billing, quota or Wi-Fi.
6. **Risk is a points score, not a model.** Explainability and regulatory wording matter more than 0.03 AUC. Thresholds
   are per person (quantiles of the score over the trailing 90 days of awake hours) so a daily-seizure user is not
   permanently "high".
7. **The trigger ladder has five rungs and a floor.** Under 10 exposures → always *watching* with a countdown.
   Notes-only evidence (imported tags with no seizure-free days) is capped at *emerging*.
8. **Overnight = "no data", never "low".** Diaries miss 86% of sleep seizures.

## 3. Module by module

### packages/contracts
- `schema/contracts.schema.json` — 16 top-level types. Key ones: `SeizureEvent`, `Dose`, `CheckIn`, `RiskNow`,
  `TriggerDefinition`, `TriggerTest`, `ClinicReport`, `DiaryEntryBatch`, `HourlyStats`, `MonthlyStats`, `BaselineStats`,
  `MedicationChange`, `Profile`, `ImportPreview`, `AnalysisAnswer`, `LiveToken`. `additionalProperties: false` everywhere.
- Enums: `SeizureType` = aware | staring | impaired_awareness | convulsive | drop | jerk | unsure (plain words in the app;
  `engine/report.py:ILAE_NAMES` maps to ILAE 2017 names for the report). `Severity` = mild | severe (severe = impaired
  awareness, convulsive, drop). `ContextTag` = shower_bath | hot | cold | exercise | travel | upset | school | unwell |
  period | hungry | screen | late_night | other. `TriggerRung` = watching | emerging | supported | not_seen_so_far | unlikely.
- `py/contracts/models.py` generated by datamodel-codegen (pydantic v2, StrEnum). `ts/contracts.ts` by
  json-schema-to-typescript. `fixtures/` 14 files.

### apps/api/engine
- `data.py` — `EngineData` (events, doses, checkins, symptoms, exposures DataFrames + `Profile` + tz). `daily_counts()`
  zero-filled daily series. `to_ns()` converts any tz-aware index to UTC nanoseconds — **always use it**; pandas 2 keeps
  microsecond units for imported datetimes and `.asi8` silently gives µs (this bit us once: "2594 seizures in the last 7 days").
  `HALF_LIFE_HOURS` working midpoints per drug; `ensure_tz()` for user-supplied timestamps.
- `importer.py` — `import_family_workbook(xlsx)` → `(events, warnings)`. Label → type via `LABEL_RULES` (first match),
  severity from the H/L column when present, context tags from notes via `CONTEXT_KEYWORDS` regexes, rescue clobazam from
  the dose column, rows without a time → 12:00 + `confidence=guess`. `redact()` replaces known names with role words and
  strips NHS-number patterns. `import_generic_csv(path, mapping)` for other diaries. `preview_from_events()` builds the
  `ImportPreview` the UI shows before commit.
- `stats.py` — `hourly_stats` (trailing 365 d by default; `vs_flat` = share × 24), `monthly_stats`, `baseline_stats`
  (90-day daily series → weekly rolling sums → p25/median/p75/p90 and a verdict for this week), `medication_change_effect`
  (±56-day windows, Poisson means test, verdict: clear rise/fall p<0.01, probable p<0.05, else "within usual range" if the
  post-week sits inside the person's 10–90% weekly band from the prior year), `cluster_days`, `seizure_free_runs`.
- `risk.py` — the score. `score_grid(data, times, as_of, trigger_rungs)` is vectorised over a DatetimeIndex via
  `np.searchsorted` on UTC-ns event times; `compute_risk()` scores one timestamp and sets the tier from `thresholds()`.
  Components (`COMPONENTS`): `hour_band` (0–4, `forward_band`: share of seizures starting in [h, h+3) vs a flat day, 0.1
  steps — forward-looking because the horizon is 3 h; this alone moved AUC from 0.62 to 0.68), `today_count` (0/0.3/0.6),
  `recent_gap` (+0.3 if <6 h), `week_vs_baseline` (+1 above p75 / +0.5 above median of trailing weekly sums),
  `dose_overdue` (+1 if a scheduled dose is > ¼ half-life late — **only active if the person has logged any dose in the
  last 14 days**, otherwise an imported diary would score every dose as missed), `dose_skipped` (+2), `feeling_off` (+2 from
  check-in or a symptom logged within 6 h), `stress` (+0.5 only when the stress trigger is emerging/supported),
  `short_sleep` (+0.5 below the person's p25 of check-in sleep, needs 14 nights). Thresholds: medium = 50th, high = 85th
  percentile of awake-hour scores over the trailing 90 days. Learning mode (<30 events in 365 d): score uses only today's
  count, gap, feeling-off and skipped dose. `overnight` from `profile.sleep_window`. Reasons: top 3 components, text from
  `_reason_text`.
- `triggers.py` — `test_trigger(data, defn, as_of, history)` → `TriggerTest`. Modes: `daily_factor` (check-in field via
  `CHECKIN_FIELD_RULES` or `daily_trigger_flags[name]`; exposed vs unexposed days among days WITH a check-in; permutation
  of labels), `exposure` (timed windows after `data.exposures` rows matching name/tag; baseline = same clock hours on
  days without the exposure; permutation moves exposures to random days; time-of-day-stratified ratio as confounder
  check), `symptom` (same with a short window over `data.symptoms`), `tag_only` fallback when the tag exists only on
  seizure rows (severe share with vs without; capped at emerging). `_rung()` encodes the ladder; `adjust_bh()` applies
  Benjamini–Hochberg across all tests and re-derives rungs/texts. `PERMUTATIONS=1000`.
- `report.py` — `build_clinic_report()` → `ClinicReport`: window vs prior window, completeness line (days with any
  entry), headline (per-28-day rate, % change, seizure days, days since last convulsive, longest run), by-type table with
  ILAE names + patient label, weekly stacked counts, medication (current from profile, changes with effects, adherence,
  rescue uses with next-3-day counts), wellbeing (check-ins; LAEP/NDDI-E/GAD-7 slots are present but null), risk factors
  as facts, triggers (supported/emerging only), `WORDING_NOTES`.
- `backtest.py` — walk-forward in 7-day blocks; thresholds and histogram from data before each block; AUC on awake hours.

### apps/api/app
- `config.py` — env (`.env` at repo or api root): `GEMINI_API_KEY`, model ids (`gemini-3.8-live`, `gemini-3.8-flash`,
  `gemini-4-argon` + fallback), `DB_PATH`, `FIXTURES_DIR`, `APP_TIMEZONE`, `CORS_ORIGINS`, `FORCE_MOCK`.
- `store.py` — SQLModel tables `seizure_event, dose, checkin, symptom, exposure, trigger_definition, trigger_test,
  medication_change, kv`. `bump_version()` on every write; `data_version()` is the cache key for `service.engine_data()`.
  `load_engine_data()` builds `EngineData` from everything.
- `service.py` — cached engine data, `risk_now(at)`, `hourly`, `monthly`, `baseline`, `run_trigger_tests(only)`,
  `list_trigger_tests()` (sorted supported → emerging → watching → not seen → unlikely), `add_trigger`, `clinic_report`.
- `main.py` — routes (see §4). `_import_jobs` is an in-memory dict (fine for a demo; a restart loses pending previews).

### apps/api/gemini
- `client.py` — lazy `genai.Client`; `None` in mock mode.
- `live.py` — `TOOL_DECLARATIONS` (log_seizure, log_dose, log_symptom, get_todays_meds), `system_instruction(profile,
  watching_triggers)` (one question at a time, read-back before saving, never dosing advice, emergency rule, greet first),
  `create_live_token()` → `LiveToken` with `token`, model id, system prompt, custom vocabulary (defaults + profile drugs),
  declarations. Real path calls `client.auth_tokens.create(config={"uses":1, "expire_time", "new_session_expire_time",
  "live_connect_constraints": {"model", "config": {"response_modalities": ["AUDIO"]}}, "http_options": {"api_version":"v1alpha"}})`
  and returns `token.name`. **Unverified against the live SDK; see §6.**
- `tools.py` — handlers write contract rows via the store and return `{status, say, ...}`; `handle(name, args)` never
  raises (the Live session stalls if a tool gets no response).
- `extract.py` — `extract(transcript)`: real path = `generate_content(model=extract_model, contents=PROMPT, config={
  response_mime_type: "application/json", response_schema: DiaryEntryBatch, temperature: 0})`; mock path = a regex
  heuristic that handles the demo line ("quarter past seven", "a minute and a half", "head went to the side", "shower").
- `analysis.py` — `ask(question, data, engine_numbers, med_csv)`: builds a prompt with the engine's trusted numbers +
  medication CSV + events CSV, calls `generate_content` with `tools=[{"code_execution": {}}]` on Argon, falls back to Flash,
  then to a mock; parses the first JSON object out of the text; returns `AnalysisAnswer` (+ base64 PNG if the model drew one).

### apps/web (for context; the UI owner has it)
`api/client.ts` typed client with `qs()` adding `mock=1`; `state/store.ts` zustand (risk, baseline, today's events,
timer, replay time); pages Home, Log (voice + typed fallback + confirm-before-save), Timeline (hour histogram, monthly
bars with medication markers, replay scrubber calling `/risk/now?at=`), Triggers (ladder + add + "ask the diary"),
Report (print stylesheet), Emergency, Import. `live/liveClient.ts` + `live/audio.ts` implement BidiGenerateContent over
WebSocket with inline AudioWorklets (16 kHz capture, 24 kHz playback), tool calls forwarded to `POST /live/tool`.

## 4. API (all under `/`, the web proxies `/api/*` → `/*`)

| Method & path | Body / params | Returns | Notes |
| --- | --- | --- | --- |
| GET `/health` | | counts, data_version, gemini on/off | |
| GET/PUT `/profile` | `Profile` | `Profile` | PUT invalidates the engine cache |
| GET `/events` | `from`, `to`, `limit` (`?mock=1`) | `SeizureEvent[]` | naive ISO localised to Europe/London |
| POST `/events` | `SeizureEvent` | saved event | |
| POST `/events/tap` | `{still_going?}` | event with `source=tap`, `type=unsure` | the quick path |
| PATCH `/events/{id}` | partial `SeizureEvent` | updated event | setting `type` re-derives `severity` |
| POST/GET `/doses`, POST/GET `/checkins` | contract models | | |
| GET `/risk/now` | `at?` | `RiskNow` | `at` = replay time |
| GET `/stats/hourly` | `at?`, `window_days?` | `HourlyStats` | |
| GET `/stats/monthly` | | `MonthlyStats` (+ medication changes) | |
| GET `/stats/baseline` | `at?`, `window_days?` | `BaselineStats` | |
| GET `/stats/backtest` | `start`, `end` | dict | slow-ish (seconds) |
| GET `/triggers` | | `TriggerTest[]` sorted by rung | runs tests if none cached |
| GET `/triggers/definitions` | | `TriggerDefinition[]` | |
| POST `/triggers` | `TriggerDefinition` | the new `TriggerTest` | re-runs BH across all |
| POST `/triggers/test` | `{only?: [ids], at?}` | `TriggerTest[]` | |
| POST `/triggers/{id}/archive` | | | archived = excluded from tests, data kept |
| GET `/report/clinic` | `window` (28/90/180), `at?` | `ClinicReport` | |
| PUT `/report/questions` | `{questions: []}` | | stored in kv |
| POST `/live/token` | | `LiveToken` | mock token when no key |
| POST `/live/tool` | `{id, name, args}` | `{id, name, response}` | browser forwards Live function calls here |
| POST `/transcripts/extract` | `{transcript}` | `DiaryEntryBatch` | |
| POST `/transcripts/commit` | `DiaryEntryBatch` | `SeizureEvent[]` | de-dupes on `transcript_hash` against tool-written rows |
| POST `/analysis/ask` | `{question}` | `AnalysisAnswer` | Argon → Flash → mock |
| POST `/import/preview` | multipart `file` (.xlsx/.csv) | `ImportPreview` | job kept in memory |
| POST `/import/commit` | `{job_id, label_mapping, replace}` | `{imported}` | |

## 5. How to run and test

```
make setup          # pip deps (+ dev) and pnpm workspace
make seed           # resets the DB, imports the diary, profile, 8 demo triggers, 46 medication changes; writes fixtures
make dev            # API :8000 (reload) + web :5173
make test           # 10 tests: import counts/redaction, hourly profile, risk shapes, learning mode, backtest thresholds,
                    # baseline verdict, ladder floor + BH, report wording, mock endpoints, seeded live endpoints
make demo-check     # tests + seed + boots API on :8010 + hits 13 endpoints + web build
make contracts      # after editing the schema; then make fixtures
```
Imports work without PYTHONPATH (`apps/api/_paths.py` adds `packages/contracts/py` to `sys.path` when `app` or `engine`
is imported). Run things from `apps/api` or via the Makefile.

Gotchas that already cost time: `python3 -I` ignores PYTHONPATH (don't use it here); `pkill -f "uvicorn ..."` kills your own
shell if the pattern is in your command line (demo_check tracks the PID instead); DST — use `tz_localize(..., ambiguous=
True, nonexistent="shift_forward")` on diary times and `to_ns()` for arithmetic; pytest collects any function named
`test_*` you import (the engine's `test_trigger` is imported under another name in tests); `model_copy(update=...)`
bypasses validation — re-validate with `Model.model_validate({**m.model_dump(), ...})` when changing enum fields.

## 6. What is NOT verified, and how to verify it (backend, in order)

1. **Ephemeral token creation** (`gemini/live.py`). With the key in `.env`: `python -c "from gemini.live import
   create_live_token; from app import store; print(create_live_token(store.get_profile()).token[:20])"`. If the SDK rejects
   config keys, consult the current docs page "Ephemeral tokens" (ai.google.dev/gemini-api/docs/live-api/ephemeral-tokens);
   the research memo recorded `uses`, `expire_time`, `new_session_expire_time`, `live_connect_constraints.model`,
   `http_options.api_version=v1alpha`. The browser then connects to
   `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContentConstrained?access_token=…`.
2. **Extractor schema** (`gemini/extract.py`). `curl -X POST localhost:8000/transcripts/extract -d '{"transcript":"…"}'`.
   If the API refuses the nested `DiaryEntryBatch` schema (deep refs, `format` keywords), pass a trimmed dict schema with
   only: seizures[{start_time, duration_s, duration_estimated, type, awareness, warning_before, context_tags, rescue_med,
   notes, confidence}], doses[], symptoms[], open_questions[]; validate the output with the full model afterwards.
3. **Argon with code execution** (`gemini/analysis.py`). `curl -X POST localhost:8000/analysis/ask -d '{"question":"Has
   moving the afternoon dose helped?"}'`. Check `model` in the response is `gemini-4-argon` and `mock` is false. Argon has no
   free tier; if billing is missing the fallback chain yields Flash. Response parsing expects a JSON object in the text;
   inline PNG parts become `chart_png_base64`.
4. **Live tool round-trip** without audio: `curl -X POST localhost:8000/live/tool -d '{"id":"1","name":"log_seizure",
   "args":{"start_time":"2026-10-31T19:15:00+00:00","duration_s":90,"type":"impaired_awareness","confidence":"probable",
   "context_tags":["shower_bath"]}}'` then `GET /events?from=2026-10-31`.
5. **Custom vocabulary**: the browser sends `inputAudioTranscription: {customVocabulary: [...]}` and retries without it if
   the setup errors mention vocabulary. If the field name differs in the current docs, fix it in `liveClient.ts:sendSetup`.

## 7. Backend task list for the next hours (priority order)

1. Verify §6.1–6.4 with the key; fix field names; keep mocks working (`FORCE_MOCK=1` must still run the demo).
2. **Dose logging surface**: `POST /doses` exists; add `GET /doses/today` returning the profile schedule merged with taken
   status (same logic as `gemini/tools.py:get_todays_meds`) so the UI can render a one-tap "taken" row. This is the
   feature the data most lacks (zero dose times in 8 years).
3. **Daily check-in defaults**: `GET /checkins/today` returning an empty `CheckIn` pre-filled with `daily_trigger_flags`
   keys for every trigger at *watching* (so the lab builds its denominator automatically).
4. **Samsung import** (optional, high demo value): a `POST /import/samsung` taking the export zip → sleep sessions as
   check-ins (`sleep_bed_time`, `sleep_wake_time`) and walks as `exposures(name="exercise")`. The analysis script in the
   research pack (`samsung_analysis.py`) shows the parsing (per-minute HR from `binning_data` JSON, sleep CSV, exercise
   CSV); only sleep + exercise are worth importing.
5. **Clinic report PDF**: server-side with WeasyPrint or ReportLab from `ClinicReport` (the print stylesheet works today).
6. **Argon wording pass** for `TriggerTest.plain_text` (optional): a `gemini/wording.py` that rewrites the engine's sentence
   under a strict template (two sentences, a number and a count, the next step, no causal language above "followed by").
   Store the engine text alongside; never let the model change the rung.
7. Nightly recompute hook (`service.run_trigger_tests()` + thresholds) — a FastAPI `repeat_every` or a cron; not needed for
   the demo.

Things to leave alone: the score weights (tuned on the backtest; changing them needs the test updated with evidence),
the ladder thresholds (10/20/30 exposures, ratio 1.3 or 1.2 with prior), the overnight rule, the disclaimer text.

## 8. Demo script the backend must support

1. Import the CSV/XLSX → `/import/preview` shows the mapping and the day/month warning → commit.
2. Tap "just had one" → `/events/tap` → timer → "tell me about it" → voice (or typed demo line) → `/transcripts/extract` →
   confirm → `/transcripts/commit` → `/risk/now` goes high with three reasons.
3. Patterns: `/stats/hourly`, `/stats/monthly` (medication markers), replay via `/risk/now?at=2019-01-29T12:00` etc.
4. Change experiment: `/stats/monthly` → `medication_changes` rows for 2025-03-05 ("within usual range") and 2025-09-01
   ("clear rise").
5. Trigger lab: `/triggers` (5 emerging, 2 watching) → `POST /triggers {"name":"after the train","kind":"exposure",
   "context_tag":"travel"}` → emerging live. "Ask the diary" → `/analysis/ask`.
6. Report: `/report/clinic?window=90` → print.

Backup for Wi-Fi failure: `FORCE_MOCK=1` and the typed transcript path; every screen still renders real numbers.

## 9. Legal/wording constraints baked into the code (keep them)

Diary + trends + report = not a medical device; a personal risk level becomes one on public release (MHRA "risk of",
EU MDR Rule 11 Class IIa, FDA device CDS). Hence: "risk over the next few hours" with reasons and the disclaimer on the
tile; "research prototype" in the UI; no "prediction", "safe", "seizure-free" (unless 12 months); ILAE names and facts in
the report; overnight = no data; notes redacted before storage; paid Gemini tier only; the Gemini API terms forbid use
that needs device clearance, so Gemini explains and never decides.
