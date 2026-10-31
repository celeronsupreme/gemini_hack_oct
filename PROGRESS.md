# Progress

## State at handover (31 Oct 2026)

Works end to end, verified by `make test` (10 tests) and `scripts/demo_check.sh`:
- Contracts (JSON Schema → Pydantic + TS), fixtures generated from the real diary.
- Engine: import (2,598 events, names redacted), risk now (forward-looking hour band + today + week vs baseline + dose
  lateness + feeling-off; per-person tiers; overnight = no data; learning mode), trigger ladder (daily factor, timed exposure,
  symptom, notes-only fallback; permutation tests; BH correction), baseline, medication change effects (46 changes with
  before/after), clinic report data, walk-forward backtest (AUC 0.69 on 2024–26, high tier 29% vs low 8%).
- API: every endpoint in CLAUDE.md, `?mock=1` on reads, tap/patch/commit paths, import preview+commit, Live token + tool
  handler, extractor (mock heuristic without a key), Argon ask (mock without a key).
- Web: six screens compile and build; charts hand-rolled; replay scrubber; trigger lab; report with print stylesheet.

## Not yet verified (needs a device + key)
- `apps/web/src/live/*`: mic capture, PCM playback, the BidiGenerateContent message shapes, custom vocabulary in setup.
  First run: open /log, Start listening, speak the demo line, watch the transcript and the tool saves panel.
- `gemini/live.py` `auth_tokens.create` config keys against the current SDK; `gemini/extract.py` response_schema with the
  DiaryEntryBatch model (fall back to a trimmed schema if the API rejects nested refs); Argon code execution response parts.

## Backend
- 31 Oct ~14:30, verified with a real key (UI seat):
  - `/live/token` mints a real `auth_tokens/…` ephemeral token for `gemini-3.8-live`. ✅
  - `/transcripts/extract` was broken: the SDK's `response_schema` rejects `additionalProperties` on the Developer API.
    **Fixed** in `gemini/extract.py` by passing `response_json_schema=DiaryEntryBatch.model_json_schema()`. Now returns a
    valid batch. Quality: typed "head went to the side" as `unsure` (the importer maps it to impaired_awareness; consider
    putting the profile's label map in the prompt), and "hasn't had her 7pm cenobamate" became an open question rather
    than a dose row.
  - `/analysis/ask` runs on real `gemini-4-argon` (mock false) with a good, caveated answer, but takes **~3 min**. For the
    demo, pre-run the question and cache it, or route live questions to Flash.
  - `/live/tool` round trip (`get_todays_meds`, unknown tool) ✅. `log_seizure` was not exercised, to keep the demo DB clean.
  - Not yet verified: the browser Live session (mic → WebSocket → audio playback, `customVocabulary` field name).
- 14:35 fix, Live session had no seizure context: the ephemeral token locked `live_connect_constraints.config` to
  `response_modalities` only (and requested v1alpha), so the browser's system prompt and tools never took effect and it
  acted as a generic chatbot. Applied the backend's `live-config-fix.patch`: `gemini/live.py:session_config()` locks the full
  config into the token, and `liveClient.ts` sends a minimal setup. Verified: a token with `custom_vocabulary` is accepted
  (no fallback), and a headless WebSocket session (text turns, same minimal setup) greets "I'm listening. What happened?"
  and asks about awareness and warning. `make test` 10/10, web build ok. Prompt nit: it asked two questions in one turn.
  Note: `realtimeInputConfig.silenceDurationMs: 700` was dropped from the client with the rest of the setup; add it to
  `session_config` if turn-taking feels too eager.
- ~14:50, timer → voice handoff + early speech (UI seat, touches api + web):
  - `POST /live/token` takes an optional `{event_id}`. `system_instruction(..., timed_event=)` adds the timed start and
    duration, says not to ask for them, and to pass that id to `log_seizure`. `log_seizure` gains an `id` param; with an id
    it merges into the existing row, and for `source=tap` rows the timer's start_time/duration win.
  - Prompt: no spoken greeting (the app shows "What happened?" on screen); first words count as the answer; one question
    per turn; log_seizure only after a yes to the read-back.
  - Web: TapButton → `/log?event=<id>`; Log shows the timed card and the opener bubble, prepends the timer facts to the
    transcript for extraction and pins them on the confirm screen, and patches the timed or tool-written row instead of
    committing a duplicate. `liveClient` opens the mic on tap and buffers audio until setupComplete.
  - Verified headless: the timed path never asks time/duration and saves once after yes, with the id; the untimed path
    asks start time first; merge keeps the timer values (scratch DB). Build ok, `make test` 10/10. Not yet tried by voice in the browser.
- 31 Oct ~15:35, Backend (UI redesign):
  - Contracts: `SeizureEvent.factors: string[]` (free text, separate from `context_tags`), `SeizureEvent.recovery_text`,
    `SeizureEvent.synthetic`, `Profile.last_appointment` (date). `make contracts` regenerated both sides; `make seed` rewrote fixtures.
  - `DELETE /events/{id}` (404 if missing, `{"ok": true}`, invalidates the cache); `store.delete_event(s)`. PATCH takes the new fields.
  - `/report/clinic?window=` is any int 1–400 (422 outside).
  - Risk `reasons[].text` is now a short third-person value ("6 pm–9 pm is her busiest stretch", "Two already today",
    "Last one 2.6 h ago"; "your" when role=self). Scores, weights, thresholds, chosen reasons and `factor` keys unchanged.
  - Trigger lab: exposure triggers (and daily factors with no check-in evidence) also match seizures whose `factors`
    equal or contain the trigger name, case-insensitive, via the notes-only path (capped at emerging). `POST /triggers
    {"name":"Skipped meal","kind":"exposure"}` → watching.
  - `scripts/backfill_demo.py` + `make demo-data` (`SEED=n`) / `make demo-data-clear`: synthetic seizures from 25 Aug to
    now from her own rate/hours/types/tags/factors, all `synthetic: true`; idempotent. Not run on app.db.
  - `tests/test_redesign.py` (6 tests); `test_api.py` live-token check now follows `gemini.live.TOOL_DECLARATIONS`
    (the `note` tool change). `make test` 16/16.

## UI
- 31 Oct, UI seat (Windows): ingested the skeleton; `make demo-check` passes (10 tests, 13 endpoints 200, web build) and
  `make dev` serves the web app on :5173 with the API proxied, in mock-Gemini mode. Makefile + demo_check.sh got a
  Windows branch; the rollup pin and esbuild allow are in pnpm-workspace.yaml; the lockfile was re-resolved (see CLAUDE.md).
- ~16:00, **UI rebuilt to the Home v5 design reference** (`references/`, plan in `docs/ui_redesign_plan.md`):
  - Removed the tab bar and the old pages (Log, Timeline, Triggers, Report, Import, Emergency).
  - Added Home, Timer, Assistant "blue room", Lead-up details sheet, Trends, Account, Export (PDF + CSV), plus the Emergency, Medicines and Privacy sheets.
  - Live agent: offered only `note` + `get_todays_meds` (`gemini/live.py`). Nothing saves until "Save to diary".
  - Verified: web build, `make test` 16/16, API live with the new routes; screenshots of Home, Trends, Account, Export and Details at 390×844 match the reference.
  - Not yet clicked through in a real browser: the timer → talk → save flow with a mic, PDF printing, the CSV downloads.
  - The replay scrubber and "Ask the diary" (Argon) have no place in the reference, so they are gone from the UI (the endpoints remain).
  - Overnight (00:00–07:00) the risk card correctly shows "No data".
- 31 Oct ~16:00, **Android APK** (Capacitor 8.6, `apps/web/capacitor.config.json`, `apps/web/android/`):
  - Built with `bash apps/web/scripts/build-apk.sh http://<pc-lan-ip>:8000`. The API base is baked in, so rebuild when the IP changes.
  - The bundle is served from `http://localhost` (androidScheme http), so the mic counts as a secure context and cleartext calls to the PC work.
  - RECORD_AUDIO and MODIFY_AUDIO_SETTINGS are in the manifest. `CAP_BUILD=1` turns off the PWA service worker for this build.
  - Toolchain is portable under `%LOCALAPPDATA%\AndroidBuild` (JDK 21 + SDK 36). `sdkmanager.bat` fails on the space in "Arthur Clark", so call it via `C:\Users\ARTHUR~1\...`.
  - The phone needs the API bound to the LAN (`uvicorn ... --host 0.0.0.0`) and port 8000 open in Windows Firewall.
  - Built and checked with aapt2 (package, permissions, bundled assets). **Not yet run on a device.** Uses the default Capacitor icon.
