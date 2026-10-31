# Seizure diary (hackathon build)

Voice-first seizure diary with a personal "risk over the next few hours" level, a trigger lab that tests any suspected
trigger on the person's own history, and a one-page clinic report. Gemini Live for voice capture, Gemini 4 Argon for
analysis and narration, a deterministic engine for every number.

```
make setup && make seed && make dev      # API :8000, web :5173
make test                                 # engine + API tests
make demo-check                           # the pre-demo gate
```

Put `GEMINI_API_KEY` in `.env` to enable voice, extraction and Argon; without it everything runs in labelled mock mode.
See CLAUDE.md for the architecture and working agreements, PROGRESS.md for what is verified.

Research prototype. Not a medical device; does not detect or predict seizures.
