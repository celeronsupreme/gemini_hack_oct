# Seizure diary — working agreements for Claude Code

A voice-first seizure diary with a personal risk level, a trigger lab and a clinic report, for people with frequent
seizures and their carers. Hackathon build; the architecture below is settled, extend it rather than re-deciding it.

## Run

- `make setup` once (Python deps + pnpm workspace), then `make seed` (imports the demo diary, writes fixtures).
- `make dev` runs the API on :8000 and the web app on :5173 (which proxies `/api` → :8000).
- `make test` must stay green. `make demo-check` must pass before anything merges to `main`.
- Gemini: put `GEMINI_API_KEY` in `.env`. Without it every Gemini path returns a labelled mock and the app still works.

### Windows (this machine)
- Run `make` from **Git Bash** (the VS Code Bash tool). `make` here is devkitPro's msys2 build. The Makefile detects
  MINGW/MSYS via `uname -s` and then uses `apps/api/.venv/Scripts/python.exe` (uv venv; `python3` is the Microsoft Store
  stub) and `pnpm.cmd` (npm's sh shim breaks under devkitPro's msys runtime). Env vars don't survive the hop from
  devkitPro make to Git bash, so `demo_check.sh` takes the interpreter as `$1`.
- `make setup` on Windows = `uv venv` + `uv pip install -r pyproject.toml --extra dev` in `apps/api`, then `pnpm install`.
- If a killed `make dev` leaves port 8000 busy, uvicorn's reloader **and its `multiprocessing.spawn` worker** are orphaned
  (netstat then shows dead PIDs holding the port). Stop both in PowerShell:
  `Get-CimInstance Win32_Process | ? { $_.CommandLine -match 'uvicorn app\.main:app' -or ($_.CommandLine -match 'multiprocessing\.spawn' -and $_.ExecutablePath -match '\\uv\\python\\') } | % { Stop-Process -Id $_.ProcessId -Force }`.
- `--reload` sometimes misses edits on Windows. If an API change doesn't show up, restart `make dev`.
- `pnpm-workspace.yaml` pins `rollup: 4.66.0` (pnpm 12's `minimumReleaseAge` rejected 4.67.2 on 31 Oct; the pin can go once
  4.67.2 is a few days old) and allows esbuild's postinstall. `pnpm-lock.yaml` was re-resolved under that policy.
- `make seed` / `make demo-check` rewrite fixtures with new UUIDs and timestamps. If the numbers didn't change, restore
  them with `git checkout -- packages/contracts/fixtures` to keep the diff clean.

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

## This checkout: the UI / artifact seat

Work here is either **UI changes in `apps/web`** or **improving a claude.ai artifact**. Don't edit `apps/api` or the
contracts from this seat; if the UI needs a field, write it under "UI" in PROGRESS.md for the backend owner.

- Routes: `/` Home (tap button + timer, risk tile, this-week baseline, today's list, Emergency link), `/log` (Live voice,
  or a typed transcript → `/transcripts/extract` → editable record → confirm → commit or PATCH the tapped event),
  `/timeline` "Patterns" (hour histogram, monthly bars with medication markers, replay scrubber → `setRiskAt`),
  `/triggers` (add trigger, rung chips, expandable numbers, archive, "Ask the diary"), `/report` (print stylesheet = PDF),
  `/emergency`, `/import` (not in the nav).
- Data flow: pages read the zustand store (`state/store.ts`) or call `api` (`api/client.ts`) directly. `VITE_USE_MOCK=1`
  appends `?mock=1`, so reads are served from fixtures while writes still hit the real API. Types come only from
  `@seizure/contracts` (`packages/contracts/ts/contracts.ts`).
- Styling: every colour/size is a token in `styles/app.css` (`--low/--medium/--high/--nodata`, `--emergency`, `--tap: 56px`).
  Charts are hand-rolled SVG in `components/Charts.tsx`. Dark tokens exist but are below the line.
- Known UI gaps: there is no emergency link on screens other than Home/TapButton (the spec says one tap from **every** screen); there are no
  provenance captions on some numbers; `/import` is unreachable from the nav; Nav uses emoji icons.
- Checks before done: `pnpm --filter @seizure/web build` (runs `tsc -b`), then look at the screen at phone width.

### Specs and artifacts
- `docs/handoff.md` is the backend session's handover: architecture, every endpoint, engine internals, what's unverified.
- `docs/implementation_plan.md` (live: https://claude.ai/artifact/ToDg8jPbLRHvjgyBtNAL4Q) is the spec: rung ladder, risk
  engine, clinic report layout, demo script. `docs/research_brief.md` (live: https://claude.ai/artifact/ANqJU9kqCAqRuBsj2gULCW)
  covers the data findings, the science and the legal wording. `docs/kickoff_prompt.md` is the original scaffold prompt.
- The `docs/*.md` files are 31 Oct snapshots. To improve an artifact, read the **live** one (Artifact `read` / Claude Docs
  tools) and publish to the same URL (`/artifact <url> <change>`).
- Numbers to quote: the backtest is **AUC 0.69** awake-hours (high tier 29% vs low 8%). The brief's 0.76 included overnight
  hours, so don't mix the two. The brivaracetam re-timing is 1/6/10 **Sep** 2025 (Excel swapped day and month).

### Data and privacy
- `data/` (repo root, gitignored except its README) holds the research CSVs and raw exports: the medication xlsx has the
  NHS number, the CSV `notes` column has the patient's first name, and there's a 47 MB Samsung export. `analysis/` is
  the research pack (uv project, reference only). Never `git add -f` these; never paste unredacted notes into artifacts.
- `apps/api/data/family_diary.xlsx` IS committed (the seed needs it). Its notes are only redacted on import.

## Priorities if time runs out

Tap + voice logging with confirm-before-save → Home and Patterns on real data → risk replay → trigger lab → clinic
report PDF → Argon `/analysis/ask`. The watch import and dark-mode polish are slides, not code.
