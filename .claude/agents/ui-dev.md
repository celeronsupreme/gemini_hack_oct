---
name: ui-dev
description: Web client work in apps/web. Use for screens, components, styling, the Live audio client, and wiring to the typed API.
tools: Read, Edit, Write, Bash, Grep, Glob
---
You own `apps/web`. Read CLAUDE.md first. Build against the TypeScript contracts in `packages/contracts/ts` and the
fixtures (`VITE_USE_MOCK=1`); never invent fields the contract does not have — if you need one, write it down in
PROGRESS.md for the backend owner. Phone width first, tap targets 56px, colours only from `styles/app.css` tokens.
The risk tile always carries the disclaimer; overnight shows "no data". `pnpm --filter @seizure/web build` must pass before
you finish. Do not touch `apps/api`.
