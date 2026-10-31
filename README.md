# Indie

Indie is a voice-first seizure diary for people with frequent seizures and their carers. It shows a personal "risk over the next few hours" level, runs a trigger lab that tests any suspected trigger against the person's own history, and produces a one-page clinic report. Gemini Live handles voice capture, Gemini 4 Argon handles analysis and narration, and a deterministic engine computes every number.

```
make setup && make seed && make dev      # API :8000, web :5173
make test                                 # engine + API tests
make demo-check                           # the pre-demo gate
make demo-data / make demo-data-clear     # fill / remove synthetic demo seizures since the real diary ended
```

Put `GEMINI_API_KEY` in `.env` to enable voice, extraction and Argon. Without it, everything runs in a labelled mock mode.

**Private data is not in this repo.** `make seed` and the engine tests need two files you get from the team, never through git: `apps/api/data/family_diary.xlsx` (the family's diary) and `apps/api/data/redact_names.json` (the real names to replace with role words, as `{"Name": "role"}`). Without the names file the importer refuses to run, so names can't reach the database, fixtures or Gemini.

See CLAUDE.md for the architecture and working agreements, and PROGRESS.md for what is verified.

Research prototype. Not a medical device; does not detect or predict seizures.
