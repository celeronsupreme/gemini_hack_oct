# Claude Code kickoff prompt — seizure diary hackathon app

Paste everything below the line into a fresh Claude Code session opened in an empty folder. Have the Gemini API key ready; it will ask for it.

---

You are setting up a monorepo for a two-person hackathon team (Google DeepMind hackathon, demo in a few hours) building **a voice-first seizure diary with a personal risk level, a trigger lab and a clinic report**, for people with frequent seizures and their carers. One of us owns the **UI**, the other owns the **backend**. Set up the `.claude` environment and the codebase so we can work in parallel from minute one without blocking each other, then build the walking skeleton. Ask me for the Gemini API key when you need it (store it in `.env`, never commit it, add `.env.example`).

## Product in one paragraph

A carer or the person themselves logs a seizure in two ways: a one-tap "just had one" (instant timestamp, optional timer) and a voice debrief through the Gemini Live API, where the model extracts everything said and asks one question at a time for anything missing (start time, duration, type / awareness, warning or aura beforehand, what they were doing just before, last dose taken, recovered yet, rescue clobazam, asleep at onset, injury, period). The home screen shows **risk now, next few hours: low / medium / high** with its reasons. The trigger lab lets the user name any suspected trigger and get an honest verdict from their own history (confirmed / not enough evidence / rejected). A one-page clinic report exports as PDF. We have 8 years of real diary data (2,598 seizures) for the demo.

## Models and APIs (verified against Google docs, 31 Oct 2026)

- Voice: `gemini-3.8-live` (Live API, WebSocket, audio in/out). Browser connects with an **ephemeral token** minted by our backend (`client.auth_tokens.create`, `uses: 1`, locked to this model). Config: `response_modalities: ["AUDIO"]`, `system_instruction`, `input_audio_transcription: {custom_vocabulary: [drug and seizure terms]}`, `output_audio_transcription: {}`, `tools: [{function_declarations: [...]}]`, `context_window_compression: {sliding_window: {}}`, `session_resumption: {}`. Function calls are NON_BLOCKING by default; we must reply with `send_tool_response`. Audio: send 16-bit PCM 16 kHz; play 24 kHz PCM. Do **not** pass `thinking_level` to this model. Structured output is not supported inside Live.
- Extraction after a session: `gemini-3.8-flash` with `response_format` / `response_mime_type: application/json` and a JSON schema over the full two-sided transcript. Reconcile with the rows written by tool calls. Confirm-before-save in the UI.
- Analysis and narration: `gemini-4-argon` (paid tier; 1M context; `tools: [{"type": "code_execution"}]`; structured JSON out). If billing isn't enabled, fall back to `gemini-3.8-flash` with the same code.
- SDKs: Python `google-genai` ≥ 2.3 (backend), JS `@google/genai` (web). Google's official browser example to crib from: `google-gemini/gemini-live-api-examples`, folder `gemini-live-ephemeral-tokens-websocket` (vanilla JS mic capture, PCM playback, function calling, `server.py` token backend) — change the model string to `gemini-3.8-live`.

## Repo layout (create it)

```
/
  CLAUDE.md                      # conventions, run commands, who owns what, demo priorities
  .claude/
    settings.json                # permissions: allow pnpm/uv/pytest/vite; deny rm -rf outside repo
    agents/ui-dev.md             # subagent: React/TS, mobile-first, never touches apps/api
    agents/backend-dev.md        # subagent: FastAPI/pandas/google-genai, never touches apps/web
    agents/reviewer.md           # read-only reviewer: checks contracts match on both sides
    commands/ui.md               # /ui <task>: work only in apps/web against packages/contracts + fixtures
    commands/backend.md          # /backend <task>: work only in apps/api, keep mock endpoints green
    commands/demo-check.md       # /demo-check: start both apps, hit every demo endpoint, open the 5 demo screens
  packages/contracts/            # the single source of truth both halves build against
    schema/*.json                # JSON Schema: SeizureEvent, Dose, CheckIn, RiskNow, TriggerTest, ClinicReport, DiaryEntryBatch
    ts/                          # generated TS types (json-schema-to-typescript)
    py/                          # generated Pydantic models (datamodel-codegen)
    fixtures/                    # realistic JSON fixtures for every endpoint so the UI never waits on the API
  apps/web/                      # React + Vite + TypeScript, mobile-first PWA (phone width first), Capacitor-ready so it can ship to iOS/Android later
  apps/api/                      # FastAPI (Python 3.12, uv), SQLite via SQLModel, pandas/numpy/scipy for the engine
  data/                          # seizures_clean.csv, medication_timeline.csv (anonymised; notes may still hold names — redact script here)
  scripts/                       # import_diary.py, redact_names.py, backfill_demo_week.py
  Makefile                       # make dev (both), make api, make web, make test, make demo-check
```

Use pnpm for the web app, uv for Python. One `make dev` must start both with hot reload. CORS open for localhost.

## The contract (write this first, then mocks, then real code)

Define these schemas in `packages/contracts/schema` and generate both TS and Pydantic from them:

- `SeizureEvent`: id, start_time (ISO), duration_s (int|null), duration_estimated (bool), type (enum: aware, staring, impaired_awareness, convulsive, drop, jerk, unsure), awareness (kept|impaired|lost|unknown), asleep_at_onset, recovered_at, injury, incontinence, rescue_med {drug, dose_mg, time}|null, warning_before (bool), warning_text, context_tags (array of enum: shower_bath, hot, cold, exercise, travel, upset, school, unwell, period, hungry, screen, other), notes, who_logged (patient|carer|watch), confidence (certain|probable|guess), possibly_non_epileptic (bool), source (tap|voice|import).
- `Dose`: drug, dose_mg, scheduled_time, taken_time|null, skipped (bool), reason.
- `CheckIn`: date, sleep_bed_time, sleep_wake_time, sleep_quality 1–5, stress 0–10, mood 0–10, fatigue 0–10, feeling_off (bool), unwell (bool), period_started (bool), alcohol_units, exercise (bool), big_event_tomorrow (bool), notes.
- `RiskNow`: tier (low|medium|high), score (float), computed_at, horizon_hours (3), reasons: [{factor, points, text}], learning_mode (bool, true under 30 events), overnight_no_data (bool).
- `TriggerTest`: trigger, verdict (confirmed|not_enough_evidence|rejected), exposure_days, seizures_after_exposure, baseline_rate, ratio, p_value, method, plain_text.
- `ClinicReport`: window (90 days), counts by type, severe count, convulsive count (12 months), nocturnal count (30 days), longest seizure, events ≥5 min, dose adherence %, rescue doses, period/sleep/stress summaries if logged, medication changes with before/after rates, confirmed and rejected triggers, questions for the clinician, logging-effort note.
- `DiaryEntryBatch`: what the extractor returns from a transcript: seizures[], doses[], checkin|null, open_questions[].

API endpoints (FastAPI, all returning contract types, all with a `?mock=1` path that serves fixtures): `POST /live/token`, `POST /events`, `GET /events?from&to`, `POST /doses`, `POST /checkins`, `POST /transcripts/extract`, `GET /risk/now?at=<iso>` (the `at` param is what makes the demo replay work), `GET /stats/hourly`, `GET /stats/monthly`, `GET /stats/baseline`, `POST /triggers/test`, `GET /report/clinic?window=90`, `POST /analysis/ask` (Argon with code execution over the CSV).

## Risk engine (backend, deterministic, in code — Gemini explains it, never computes it)

Hourly score, with components and points (from our own backtest on this diary, which is why time of day is weighted so heavily):

- Time-of-day band from the person's own hourly histogram: 0–2 points (this hour's share > 2× a flat day = 2; > 1× = 1). On the demo diary 75% of seizures start 12:00–22:00, peak 19:00.
- Seizures so far today: 0 / 1 / 2 points for 0 / 1 / 2+.
- Under 6 h since the last seizure: +0.5.
- Last 7 days vs the person's 90-day baseline: +1 above the 75th percentile, +0.5 above the median.
- A scheduled dose overdue by more than a quarter of its half-life: +1; a skipped dose: +2 (brivaracetam ~9 h, levetiracetam 6–8 h, clobazam 10–30 h, cenobamate 30–76 h, lamotrigine 15–35 h).
- `feeling_off` or a warning symptom logged in the last 6 h: +2.
- Stress ≥ 7 today: +0.5, only once the person's own data show the link (skip for the demo unless synthetic).

Tier thresholds are set **per person** so that over the trailing 90 days "high" covers ~15% of hours and "low" ~50%. Between midnight and 07:00 return `overnight_no_data: true` and show "no data" rather than "low". Under 30 logged events return `learning_mode: true` and show only today's count and time since last seizure. Hard safety rules run outside the score: timer passes 5 min (convulsive) or 10 min (other) → emergency screen; today's count above the person's own 90th percentile, or 3 in 24 h, or 2 in 6 h → cluster alert.

Backtest target to reproduce as a test (train ≤ 2023, test 2024–Aug 2026 on `data/seizures_clean.csv`): "any seizure in next 3 h" AUC ≈ 0.76; high tier ≈ 25% hourly hit rate vs low ≈ 3.4%.

## Trigger lab (backend)

`POST /triggers/test` takes a trigger name plus either a context tag, a check-in field, or a free-text keyword. Method: exposure days vs non-exposure days in the window, seizure rate ratio with a permutation test (≥ 1,000 shuffles), Benjamini–Hochberg across all triggers tested so far, minimum 10 exposure days before any verdict other than "not enough evidence", and a confounding-by-indication check for rescue meds. Return `TriggerTest` with plain text written by Argon (or Flash) from the numbers. For the demo, pre-run: hot shower/bath, period, travel, exercise, upset — the diary's notes support these.

## UI (apps/web), phone-width first, five screens

1. **Home**: big risk tile (tier colour, "next few hours", three reasons in plain words, "research prototype — not a prediction" footer), the "just had one" button (starts a timer; a second tap stops it and opens the voice debrief), today's strip of events, and an emergency card one tap away (999/112, 5-minute rule, recovery position).
2. **Voice debrief**: mic button, live transcript of both sides, the record filling in field by field as tool calls land, confirm-to-save. Use the Google example's audio worklet code.
3. **Timeline**: calendar heat-strip + hour-of-day histogram + monthly bars with medication changes marked; a scrubber that calls `/risk/now?at=` so we can replay a real day hour by hour.
4. **Trigger lab**: list of tested triggers with verdict chips; "test a new trigger" input; each result expands to the numbers and a one-line method.
5. **Clinic report**: rendered report, "Export PDF" (server-side via WeasyPrint or client-side print stylesheet).

Visual direction: calm, high contrast, large tap targets (carers are often kneeling on the floor with one hand), no red except the emergency card and the high tier. Dark mode later.

## Working agreements (put these in CLAUDE.md)

- Contracts change only via a PR that regenerates both TS and Pydantic and updates fixtures; the reviewer agent checks every PR touches contracts, fixtures, or neither.
- Backend keeps `?mock=1` green at all times; UI develops against mocks and flips to live by env flag.
- Branches: `ui/*` and `api/*`; `main` is always demo-able; `make demo-check` must pass before merging.
- Never send names or the NHS number to Gemini: run `scripts/redact_names.py` over notes on import; only the paid tier.
- The system prompt for the voice agent: one question at a time, never more than three per entry, start with time and duration, accept vague answers with `duration_estimated: true`, read the record back in one sentence before saving, never give dosing advice, read the emergency plan if the timer passes the threshold. Load the person's drug names and top triggers into the prompt and the transcription custom vocabulary.
- Every screen that shows a number also shows where it came from.

## Build order (stop when time runs out; each step is demo-able on its own)

1. Repo scaffold, `.claude` files, contracts, generated types, fixtures, `make dev`, `make demo-check` — both of us can start.
2. Import the real diary into SQLite; `/stats/*` and `/risk/now?at=` from real data; Home + Timeline against them.
3. Voice debrief end to end: token endpoint, Live session with four tools (`log_seizure`, `log_dose`, `log_symptom`, `get_todays_meds`), post-session extraction, confirm-to-save.
4. Trigger lab with the five pre-run triggers.
5. Clinic report + PDF.
6. `/analysis/ask` with Argon code execution ("has moving the afternoon dose helped?").
7. Only then: watch/HealthKit, dark mode, accounts.

Start now: scaffold, write CLAUDE.md and the `.claude` files, generate the contracts and fixtures, and get `make dev` running with the Home screen rendering from fixtures. Then ask me for the Gemini API key and wire the token endpoint. Keep a running `PROGRESS.md` with what works, what's mocked, and what's next, so whichever of us opens the repo next knows where it stands.
