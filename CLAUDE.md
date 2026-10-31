# Seizure diary — working agreements for Claude Code

A voice-first seizure diary with a personal risk level, a trigger lab and a clinic report, for people with frequent
seizures and their carers. Hackathon build; the architecture below is settled, extend it rather than re-deciding it.

## Run

- `make setup` once (Python deps + pnpm workspace), then `make seed` (imports the demo diary, writes fixtures).
- `make dev` runs the API on :8000 and the web app on :5173 (which proxies `/api` → :8000).
- `make test` must stay green. `make demo-check` must pass before anything merges to `main`.
- Gemini: put `GEMINI_API_KEY` in `.env`. Without it every Gemini path returns a labelled mock and the app still works.

## Layout

- `packages/contracts/schema/contracts.schema.json` — the ONLY place record shapes are defined. `make contracts`
  regenerates `py/contracts/models.py` (Pydantic) and `ts/contracts.ts` (TypeScript). Never edit the generated files.
- `packages/contracts/fixtures/*.json` — one fixture per endpoint, written from the real diary by `make seed`.
  Every read endpoint serves its fixture with `?mock=1`; the web app uses them with `VITE_USE_MOCK=1`.
- `apps/api/engine/` — pure Python, no I/O: `risk.py` (points score, per-person tiers), `triggers.py` (five-rung ladder),
  `stats.py`, `report.py` (clinic report data), `importer.py`, `backtest.py`. Tested in `apps/api/tests/test_engine.py`.
- `apps/api/app/` — FastAPI: `main.py` (routes), `service.py` (engine over the store, cached by data version), `store.py`
  (SQLite; each row keeps its contract JSON in `payload`), `config.py` (env).
- `apps/api/gemini/` — the only code that talks to Google: `live.py` (ephemeral tokens, system prompt, tool declarations),
  `tools.py` (tool handlers → store), `extract.py` (transcript → DiaryEntryBatch), `analysis.py` (Argon with code execution).
- `apps/web/src/` — React + Vite PWA, phone width first. `api/client.ts` typed client; `state/store.ts` zustand;
  `pages/*` the six screens; `components/*`; `live/*` the Gemini Live WebSocket + audio worklets (test on a real device);
  `styles/app.css` design tokens (Claude Design restyles here).

## Rules

1. Contracts change only in the schema, with `make contracts` and updated fixtures in the same commit; the reviewer agent
   checks this.
2. The engine computes every number the user sees. Gemini explains, narrates, extracts and answers free-text questions;
   it never produces the risk tier or a trigger verdict.
3. The trigger ladder never says "rejected" for lack of data. Rungs: watching → emerging → supported / not seen so far /
   unlikely. Fewer than 10 exposures is always "watching". Imported notes-only tags are capped at "emerging".
4. Overnight hours show "no data", never "low". Under 30 events the risk tile is in learning mode.
5. Wording: "risk over the next few hours", never "prediction"; the disclaimer stays on the tile; ILAE names in the
   report; facts not diagnostic labels; never "seizure-free" unless 12 months.
6. Privacy: `engine.importer.redact` runs on every note before storage; nothing with a real name or the NHS number reaches
   Gemini; paid tier only. The demo uses the anonymised family diary already in `apps/api/data/`.
7. Backend keeps `?mock=1` working at all times. UI develops against mocks and flips to live by env flag.
8. Branches `ui/*` and `api/*`; `main` is always demo-able. Update `PROGRESS.md` at the end of every session.

## Who owns what

- `/backend <task>` works only in `apps/api` and `packages/contracts` (regenerating both sides).
- `/ui <task>` works only in `apps/web` against the contracts and fixtures.
- `/demo-check` runs `scripts/demo_check.sh` and reports what failed, nothing else.

## Priorities if time runs out

Tap + voice logging with confirm-before-save → Home and Patterns on real data → risk replay → trigger lab → clinic
report PDF → Argon `/analysis/ask`. The watch import and dark-mode polish are slides, not code.
