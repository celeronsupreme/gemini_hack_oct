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
- (add here)

## UI
- (add here)
