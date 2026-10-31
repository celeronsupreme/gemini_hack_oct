# UI redesign plan: build the Home v5 reference

Source of truth for layout, copy and motion: `references/DESIGN_HANDOFF.md` and `seizure-app-design/design/Main.dc.html` (final variants only: home "glow" risk card, details "timeline", assistant "room"). Data, safety rules and endpoints follow `docs/implementation_plan.md`. Status: **built (31 Oct ~16:00)**; decisions at the bottom.

## The new shape

The bottom tab bar and the five separate pages (Home, Log, Patterns, Triggers, Report) go. There is one Home screen, and everything else opens from it:

```
Home ── avatar ─────────────▶ Account ──▶ Export sheet (PDF clinic report | CSV)
 │                                    ├─▶ Medicines · Emergency plan · What the assistant sees
 ├── Today card "Trends ›" ──▶ Trends (last 7 days · time of day · by month + medication markers)
 ├── Today card time pill ───▶ Seizure details sheet ("Lead-up" timeline)
 └── Seizure bar ────────────▶ Timer (blue) ── It's over ──▶ Stopped ── Tell me about it ──▶ Assistant (blue room) ── Save to diary ──▶ Home + toast
                                                                     └── Done ──▶ Home + toast
```

Screens are pushed and popped with the reference's motion (`transform .55s cubic-bezier(.3,.9,.3,1)`), driven by a small screen state in the store rather than routes. The design is a stack of overlays, not pages. Home must fit 390×844 with no scrolling.

## Screen by screen, with real data

| Screen | What it shows | Where the data comes from | Gaps / work |
| --- | --- | --- | --- |
| **Home header** | Date, person's name, avatar initial | `GET /profile` (`display_name`, `role`) | none |
| **Risk card** | Tier word (gradient), 3-step meter, 3 key/value reasons, fixed 9.5px disclaimer; overnight = "No data" + grey meter + "Nothing is logged while she sleeps…"; learning mode | `GET /risk/now` | Engine reason text is long and second person ("19% of your seizures start between…"). **Backend:** short third-person text + a key per factor (hour_band → "Time of day", today_count → "Today", week_vs_baseline → "This week", dose_* → "Medication", feeling_off → "Warning signs", short_sleep → "Sleep"). The reference's "Period cycle" reason doesn't exist in the engine (no menstrual pattern in her data), so it won't appear. |
| **Today card** | Count, time pills on a 24h track (2 lanes, stacked within 3.6 h), now marker, "Trends ›", counters "N convulsive · 12 months", "N at night · 30 days" | `GET /events?from=<start of day>`; counters from `GET /events?from=<12 months ago>` computed client-side | none (the counters may be small: 9 convulsive events in 8 years) |
| **Seizure bar** | Glass dock, blue "● Seizure" | `POST /events/tap` fires after the timer is already running (never waits on the network) | none |
| **Timer** | Blue full screen, "Timing" blink, mm:ss, "Started 18:40", 5 one-minute bars, "It's over", Discard | Local timer; tap event id from `/events/tap` | **Backend:** `DELETE /events/{id}` for Discard. Emergency: see Q4. |
| **Stopped** | "Lasted 1m 32s · started 18:40", "Tell me about it" / "Done" | `PATCH /events/{id}` with `duration_s` | none |
| **Assistant (blue room)** | White breathing orb + state (Listening / Speaking / Paused / All noted), current line word-by-word at 29px, "Picked up" panel: THE SEIZURE chips, BEFORE IT chips, "Track X?" cards, mic toggle, "Save to diary" | Live session (already working: the token carries the timed start and duration). Listening or Speaking comes from audio activity; the current line comes from the input/output transcription streams. | **Chips must appear while she talks**, and the reference says the assistant never auto-saves. Plan: add a non-writing Live tool `note(kind, label)` (kind = what_happened / awareness / before / medication / new_factor) that only feeds the chips; drop the "call log_seizure after yes" rule; **Save to diary** runs the Flash extraction on the transcript, removes anything whose chip the user deleted, and PATCHes the tapped event (plus doses). The typed fallback stays, hidden behind a small "Type instead" link, for when Gemini is off. |
| **Seizure details ("Lead-up")** | Big editable start time, Lasted, Aware toggle, 24h strip; "Leading up to it" vertical timeline with a rung caption per factor; "Add to the timeline" catalogue + "Your own"; rows What happened / Recovery / Notes / Logged; Delete | `SeizureEvent` (`PATCH`, `DELETE`); rung captions from `GET /triggers` | The catalogue has Missed dose, Poor sleep, Stress, Tired, Alcohol and free-text "Your own", none of which are in `context_tags`; Recovery is free text, but `recovered_at` is a time. See Q3. |
| **Trends** | Last 7 days bars with a "her usual" dashed line; Time of day (12 months, peak bar highlighted, "75% between midday and 10 pm"); By month (12 months) with numbered medication markers and one-line verdicts; Triggers card; footer disclaimer | `/events` (7 days) + `/stats/baseline` (`weekly_median`/7); `/stats/hourly`; `/stats/monthly` (`months`, `medication_changes[].verdict`, before/after); `/triggers` | The real diary ends 24 Aug 2026, so "last 7 days" and "October" are empty apart from today's test entries. See Q2. Triggers card: see Q1. |
| **Account** | Profile card; REPORTS AND EXPORT (Clinic report, Export her diary, Share with her nurse); HER CARE (Medicines, Emergency plan, Triggers she's testing); PRIVACY (What the assistant sees, Delete her data) | `/profile` | "Share with her nurse" and "Delete her data" have no backend; they show the reference's toast and a confirm dialog, clearly mocked. |
| **Export sheet** | Format PDF / CSV; Covers: Since last visit / 90 days / 12 months; PDF page-1 preview + switches (Event log, Emergency care plan, Trigger lab, Her questions); CSV file list; glass "Export PDF/CSV" button, toast | PDF: `GET /report/clinic?window=` rendered into a print-only A4 page, then `window.print()`. CSV: built in the browser from `/events`, `/doses`, `/checkins`. | **Backend:** allow `window=365`. "Since last visit" needs a last-appointment date that `Profile` doesn't have (see Q3); until then it falls back to 90 days and says so. |

Kept from the current app and restyled: the emergency plan content (`Emergency.tsx`), the Live client and audio worklets, the API client and contracts. Removed from the UI: the bottom nav, `/log`, `/timeline` (including the replay scrubber, which the reference doesn't have, so the "scrub 29 Jan 2019" demo beat goes unless we add it back later), `/triggers` (the add-a-trigger form and "Ask the diary"), `/report`, `/import`.

## "Aren't Flash and Argon already picking out triggers from what I say?"

Only partly:
- **What happens today:** after a conversation, Flash tags the seizure with any of 13 fixed context tags it hears (shower/bath, hot, travel, period, upset, school, unwell, exercise, late night, screen, hungry, cold, other). The trigger engine then tests the 8 pre-set triggers against those tags, with deterministic statistics.
- **What doesn't happen:**
  - Something new ("she skipped lunch", "exam nerves") only lands in the notes. Nothing turns it into a trigger to watch.
  - Argon isn't involved in triggers at all. It only answers the "Ask the diary" box, and takes ~3 minutes.
- **The redesign's part:** the `note(kind="new_factor")` tool picks new factors up live (the reference's "Track 'Skipped meal'?" card), and the engine starts testing them automatically. Gemini still never decides a verdict, because the number has to come from the engine (the regulatory point in the plan). Gemini proposes; the engine tests.

## Backend changes this needs (small, all behind existing contracts unless Q3 says otherwise)

1. `DELETE /events/{id}`.
2. Short third-person `reasons[].text` with a stable `factor` key (wording test updated).
3. `/report/clinic?window=365`.
4. Live: `note` tool (no DB write), prompt no longer calls `log_seizure` itself; keep `log_dose` and `get_todays_meds`.
5. Depending on answers: demo clock (Q2), auto-tracking new factors (Q1), contract fields (Q3).

## Build order (each step demo-able)

1. Tokens (exact values from the handoff), Onest font, icon set (the reference's `IC` stroke paths), card / glass-dock / sheet / toast primitives, screen-stack shell; delete the nav.
2. Home: header, risk card (incl. overnight + learning states), Today card with pills, Seizure bar.
3. Timer + Stopped (+ Discard, emergency per Q4).
4. Assistant blue room on the existing Live session + `note` chips + Save.
5. Seizure details (Lead-up) sheet.
6. Trends.
7. Account + Export (PDF print page, CSV).
8. Cleanup, `make demo-check`, screenshots at 390×844 against the reference renders.

## Decisions (31 Oct, answered by the UI owner)

- **Q1, trigger lab: build it exactly as the reference draws it.** That means the Trends "Triggers" card, the rung captions in Lead-up, the "Track X?" ✓/✕ cards in the assistant (✓ → `POST /triggers`, watching), Account → "Triggers she's testing" (opens Trends), and the Export "Trigger lab" switch.
- **Q2, clock: real today**, plus a way to create fake demo data for the gap since 24 Aug: `apps/api/scripts/backfill_demo.py` generates seizures from her own patterns, every row flagged `synthetic: true`, with a matching remove command.
- **Q3, contract: add the fields.** `SeizureEvent.factors: string[]`, `SeizureEvent.recovery_text`, `SeizureEvent.synthetic`, `Profile.last_appointment`. Both sides regenerated, fixtures updated, and the engine tests triggers against `factors` as well as `context_tags`.
- **Q4, emergency: as drawn.** The card appears on the timer at 5:00 and under Account → Emergency plan.
