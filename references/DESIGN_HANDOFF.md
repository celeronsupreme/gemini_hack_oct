# Seizure app: design handoff for Claude Code

This folder holds the approved mobile design for the hackathon demo (Home v5, 31 Oct 2026). Build `apps/web` to match it. The design is the source of truth for layout, copy and motion. The implementation plan (`Seizure App · Hackathon Implementation Plan`) is the source of truth for data, safety rules and endpoints.

## What's in this folder

| File | What it is |
| --- | --- |
| `design/Main.dc.html` | **The whole design in one file**: every screen, state and animation. Read this first. |
| `design/Final-*.dc.html` | Final screens, side by side: Home, Account, Export, Seizure details, Assistant. Each one just mounts `Main` at a different start screen. |
| `design/Details-*.dc.html`, `design/Assistant-*.dc.html` | Rejected alternatives, kept for reference only. **Don't build these.** |
| `design/support.js` | Design-tool runtime that lets the `.dc.html` files open in a browser. **Not app code.** |

How to read a `.dc.html` file: the markup inside `<x-dc>` is the layout, with every style inline. `{{ name }}` holes are filled from `renderVals()` in the `<script type="text/x-dc">` block at the bottom. `<sc-if>` is a conditional, and `<sc-for>` is a loop. All demo data, copy and state logic live in that script. Port the markup to React components. Don't ship the runtime.

To view it, serve the folder (`python3 -m http.server`) and open `design/Main.dc.html`. The left panel is a design-review control panel. **Don't build the panel.**

## Final decisions, and why

1. **The Seizure bar sits directly under the two home cards, 12px gap.** It's the most important action, so it lives in the thumb zone. It must not float at the bottom of the screen with dead space above it.
2. **Home fits one viewport on a 390×844 phone, with no scrolling.** Top to bottom: header, risk card (`flex: 1`), Today card, Seizure bar. Gaps between them are 12px.
3. **Risk card: word + 3-step meter, centred.** The risk word (Low / Medium / High / No data) is 56px/750 weight, filled with a subtle vertical gradient of the tier colour. A 3-bar stepped meter sits to its right (bars 26/38/50px wide, 12px tall, lit bottom-up for tier 1–3). The group is centred horizontally and vertically in the space between the header row and the reasons. **No glow, no hourly forecast tiles, no extra widgets.** Whitespace around the group is intentional.
4. **Three reasons under the risk word**, as key/value rows (`Time of day — 7 pm is her peak hour`). They come from `RiskNow.reasons[]`.
5. **The disclaimer is small (9.5px) and pinned to the bottom of the risk card.** The text is fixed: "A pattern from her own diary, not a prediction. Low never means safe. Research prototype." It's a guardrail from the plan, so make it smaller, never remove it.
6. **Seizure details = "Lead-up" timeline.** Tapping a time pill on the Today card opens a sheet:
   - **Hero card:** the start time is big (40px) and editable as text, "Lasted" sits beside it, with an Aware / Not aware toggle pill. A mini 24h strip shows today's seizures.
   - **"Leading up to it":** a vertical timeline, earliest first ("Last night · Poor sleep" → "Just before · Hot shower" → the blue Seizure node). Each node shows its trigger-lab rung and stat in the rung colour.
   - **"Add to the timeline":** pills for her catalogue of triggers, plus a "Your own" input.
   - **Rows:** What happened, Recovery, Notes, Logged (source).
   - **Delete:** "Delete this seizure" at the bottom.
   - Why: it mirrors the trigger lab's time windows (exposure 6–24 h, symptom 1–6 h), so what carers enter is already in the shape the engine tests.
7. **Assistant = "Blue room".** After "Tell me about it", the screen stays in the full blue of the timer:
   - **Top:** a white breathing orb, the state (Listening / Speaking / Paused / All noted), and the current line word-by-word at 29px, white.
   - **Panel:** a white panel rises from the bottom: "Picked up", with chips under THE SEIZURE and BEFORE IT. New-trigger suggestions show as dashed cards with ✓ / ✕ ("Track 'Skipped meal'?").
   - **Buttons:** a mic toggle and a full-width "Save to diary".
   - Why: no context switch from the timer, calm for a stressed carer, and the record builds visibly, which matches the plan's "read it back before saving".
8. **Account opens from the avatar (top right).** The order is Reports and export first, then Her care, then Privacy:
   - **Clinic report:** opens the export sheet in PDF mode.
   - **Export her diary:** opens the export sheet in CSV mode.
   - **Share with her nurse:** a read-only link that expires in 7 days.
   - **Medicines; Emergency plan; Triggers she's testing** (opens Trends).
   - **What the assistant sees** ("Names and NHS number removed first"); **Delete her data**.
9. **Export sheet:**
   - **Format:** PDF report / CSV data.
   - **Covers:** Since last visit (default) / 90 days / 12 months, each compared with the same-length prior window, as the plan's clinic report requires.
   - **PDF:** a page-1 preview, plus switches for Event log, Emergency care plan, Trigger lab, Her questions.
   - **CSV:** lists `seizures.csv`, `doses.csv`, `checkins.csv`.
   - **Export button:** in the same glass dock as the Seizure bar. It closes the sheet and shows a toast ("Clinic report saved · PDF").

Rejected (kept in the folder; don't build them): details as Tiles or Bubbles, assistant as Glow card or Day track, the risk glow orb, hourly risk tiles on the home card.

## Design tokens

Use these exactly.

| Token | Value | Use |
| --- | --- | --- |
| `bg` | `#F2F2F7` | App background |
| `card` | `#FFFFFF`, radius 22px, padding 16–18px | Every card |
| `ink` | `#1C1C1E` | Primary text |
| `ink-2` | `#3C3C43` | Secondary text |
| `ink-3` | `#6C6C70` | Labels, captions (passes 4.5:1 on white) |
| `hairline` | `0.5px solid rgba(60,60,67,.2)` | Row dividers |
| `blue` | `oklch(0.53 0.2 257)` | Primary action, Today, assistant, selection |
| `blue-soft` | `oklch(0.95 0.03 257)` | Chip and icon backgrounds |
| `low` | `oklch(0.72 0.17 150)` (text `oklch(0.5 0.13 150)`) | Risk tier |
| `medium` | `oklch(0.77 0.16 65)` (text `oklch(0.56 0.15 55)`) | Risk tier |
| `high` | `oklch(0.65 0.21 25)` (text `oklch(0.53 0.2 25)`) | Risk tier |
| `overnight` | `#6C6C70` | "No data" |
| Rung: Supported | bg `blue`, fg white | Trigger lab |
| Rung: Emerging | bg `oklch(0.94 0.05 70)`, fg `oklch(0.48 0.12 55)` | Trigger lab |
| Rung: Watching | bg `#E9E9EB`, fg `#3C3C43` | Trigger lab |
| Rung: Unlikely | bg `#F2F2F7`, fg `#6C6C70` | Trigger lab |
| Font | `-apple-system, 'SF Pro Text', 'Onest', sans-serif` (Onest from Google Fonts as the fallback) | Everything |
| Type scale | 34/700 large title · 56/750 risk word · 32/700 counts · 15/600 card labels · 14–15 body · 12.5 captions · 9.5 disclaimer | |
| Glass dock | `rgba(255,255,255,.78)`, `backdrop-filter: blur(20px) saturate(1.6)`, radius 42, height 84, inner button radius 32 | Seizure bar, Save, Export |
| Motion: screens | `transform .55s cubic-bezier(.3,.9,.3,1)` | Push/pop and sheets |
| Motion: pops | `cubic-bezier(.34,1.56,.64,1)` | Chips, pills, toggles |
| Motion: rows in | `rowIn .45s cubic-bezier(.2,.9,.3,1)` (12px rise + fade) | New rows |

Icons are 24-unit stroke paths, 1.9 stroke, round caps. Every path is in `IC` in the script, so reuse them or swap in an icon set with the same weight. **No emoji.**

## Screen map and data

| Screen | Opens from | Data (plan endpoint) |
| --- | --- | --- |
| Home: risk card | — | `GET /risk/now` → `tier`, `reasons[]`, `overnight_no_data`, `learning_mode` |
| Home: Today card | — | `GET /events?date=today`. Pills sit at the time of day and stack into 2 lanes when within 3.6 h; tap opens Details. Counters: convulsive in 12 months, night-time in 30 days (never blended into the tier). |
| Timer | Seizure bar | Writes `SeizureEvent{source:'tap'}` immediately on tap. One bar per minute up to 5. |
| Assistant (Blue room) | "Tell me about it" | Gemini Live tools `log_seizure`, `log_dose`. Chips = tool rows. Suggestions → `POST /triggers/test`. |
| Seizure details (Lead-up) | Today pill | `SeizureEvent` patch; factors → `context_tags`; rung and stat from `GET /triggers` |
| Trends | Today card | `/stats/hourly`, `/stats/monthly`, `/triggers` |
| Account | Avatar | Profile |
| Export | Account | `GET /report/clinic?window=` (PDF); CSV from `/events`, doses, check-ins |

## Behaviour rules to keep

- Overnight: the tier word is "No data", all meter bars are grey, and the card says "Nothing is logged while she sleeps, so there's no score until morning." Never show "Low" at night.
- The Seizure bar never waits for the network or the model: tap, then timer, then the event is written.
- The assistant never auto-saves. It reads the record back, then the user taps "Save to diary". Removing a chip removes that fact.
- Trigger stats always carry a number and a rung ("Supported · 2.1× for her"). Never use causal wording.
- Touch targets are 44px or more; icon-only buttons have `aria-label`; the meter has `role="img"` with an aria label like "Medium risk, level 2 of 3".
- The emergency card (999 / 5-minute rule) must be one tap from every screen. It isn't drawn yet; put it on the timer at 5:00 and in Account → Emergency plan.

## Demo-only parts (don't ship)

- The left control panel and the `startScreen`, `bare`, `detailStyle`, `assistantStyle` props.
- The scripted conversation in `LINES` (it stands in for Gemini Live).
- Fixed numbers (2.1×, 36 in October, 7 pm peak). Use these as fixtures that match the plan's demo diary.

## Suggested build order

1. Tokens and the card / glass-dock primitives.
2. Home: risk card, Today card, Seizure bar.
3. Timer.
4. Seizure details (Lead-up).
5. Blue room assistant.
6. Account + Export.
7. Trends.

Build against `?mock=1` fixtures first.
