# Seizure Tracking App — Research & Data Analysis Brief

Oct 31, 2026 · @BigP

## TL;DR

**Value statement.** Log a seizure by voice in ten seconds. See today's risk level and the reasons behind it. Test any trigger you suspect against your own history, not a textbook list. Hand your neurologist a one-page report instead of a spreadsheet. Built for the families who already keep the diary and get nothing back from it.

Build a carer-first voice diary that computes a personal baseline and a "risk now, next few hours" level from the person's own log, explains every number, and produces a clinic report. Lead the pitch with logging, baseline and trigger discovery; keep prediction a supporting act, because the evidence (and your own data) says day-ahead forecasting from diaries does not work and hours-ahead does.

Three things your data supports:

1. **Time of day dominates.** 75% of 2,598 seizures over 8 years start between midday and 22:00 and the severe ones peak at 19:00, right before the evening dose. The clock alone gives AUC 0.76 for "a seizure in the next 3 hours"; a three-tier level puts 25% hourly risk in the high tier against 3.4% in the low tier. Day-ahead forecasting scores AUC 0.54, so do not promise it. The one medication change with a clear effect is the September 2025 brivaracetam re-timing that removed the 14:00 dose: seizures after 15:00 rose 1.67-fold over the following year while mornings did not (confounded by a term start on the same day, but worth raising with her team).
2. **Clusters are real but made of small seizures.** The chance of a seizure tomorrow climbs from 45% after a quiet day to 73% after three or more; a quiet week (0 to 1) gives a 26% chance today against 61% after a busy one. Severe seizures are not predicted by counts.
3. **The notes hold the triggers the fields never captured.** Heat and hot showers, periods and travel show up with 56 to 63% severe seizures against 38% overall; "felt it coming" entries are mostly mild, aborted events. Stress and tiredness are mentioned often but do not separate severe from mild.

What to change about the idea (full critique in its own section): make the headline metric "risk now" with reasons, not a forecast; add a one-tap "just had one" so voice is the enrichment layer, not the only path; decide the user is the carer of someone with frequent seizures; log actual dose times, the biggest hole in 8 years of data; keep the watch to detection of convulsive seizures and sleep timing; ship a clinic report, which is what the family already builds by hand in Excel.

Gemini: `gemini-3.8-live` for voice (function calling, transcription with drug names as custom vocabulary), `gemini-3.8-flash` for JSON extraction, `gemini-4-argon` (paid tier, 1M context, code execution) for analysis and narration; "Jev" is not a Google model. Compute the risk tier in your own code and let Argon explain it.

Legality: a diary with trends and a clinic report is not a medical device anywhere; a personal high/medium/low risk level becomes one in the UK, EU and US the day real users can download it (MHRA treats "risk of" and "predicts" as device claims; EU Rule 11 Class IIa; FDA device CDS). The hackathon demo is fine if labelled a research prototype and run on anonymised or synthetic data; strip the NHS number and family names before anything goes to Gemini, and use the paid tier only.

## What's in your data

You have an 8-year seizure diary of 2,642 events (25 Jul 2018 to 24 Aug 2026) with clock time, duration, a type label, severity and 786 free-text notes, plus a complete medication history. That is far more than "mostly temporal": it is enough to test for weekly and monthly cycles, time-of-day peaks, clustering and medication-change effects, and to drive a convincing demo.

| Source | What it holds | Coverage | Good for |
| --- | --- | --- | --- |
| Seizure Data tab (Seizure Duration Analysis.xlsx) | One row per seizure: date, clock time (2,608 rows), duration mm:ss (2,641 rows, median 33 s, max 10 min), type label (\~10 recurring phrases, 88 blank), severity H/L (791 H / 1,763 L), clobazam rescue dose (229 rows), period-day flag (12 rows), notes (786 rows) | Jul 2018 to Aug 2026, 2,642 events | Time-of-day, clustering, cycles, severity trends, mining notes for triggers |
| Meds Changes tab (Medication Chart.xlsx) | Every regimen change per drug with the family's stated reason (lamotrigine, carbamazepine, oxcarbazepine, levetiracetam, brivaracetam, cenobamate, clobazam, lacosamide, prednisolone, plus IVIG, rituximab, keto diet, VNS mentioned) | Jul 2018 to Oct 2025 | Medication timeline; seizure rate before vs after each change |
| Current tab | Today's regimen: brivaracetam 100 mg 09:00 and 150 mg 21:00, cenobamate 350 mg 19:00, clobazam 10 mg as needed to break clusters | Oct 2025 | Seed for the app's medication schedule |
| \~150 weekly tabs | Planned dose times per drug per day; the "Done" columns are empty | Jul 2018 to Jun 2021 | Regimen reconstruction only |
| Meds Levels, Holiday tabs | Stock-tracking templates, no data | — | Nothing |

Notes coverage is uneven: 88% of 2020 events have a note, 0% of 2024 and 2025, 18% of 2026 so far. Trigger mining therefore rests mostly on 2019 to 2022.

What is missing, and what the app should add:

- Actual medication times. The chart records when doses were *scheduled* (08:00/20:00, later 07:00/14:00/21:00), never when they were given. Time-since-last-dose is the single most useful signal the app can add.
- Seizure-free days. A day with no row is ambiguous: no seizure, or nobody logged. Notes such as "GUESS 30 secs" and "assumed seizure" show events were sometimes estimated or missed.
- Sleep, stress, mood, illness, heat, exercise and menstrual cycle exist only as words in notes, never as fields. Only 12 period-start days are flagged across 8 years.
- 44 rows have no seizure date (diary-only entries or blanks) and 91 rows have duration 0; type labels have spelling variants and "#Unsure" suffixes that need normalising.
- Some dates in Meds Changes were typed as text (d/m/yy) and some were parsed by Excel with day and month swapped. The rule: for every date Excel stored as a datetime, the stored month is the typed day ("2023-04-07" is 4 Jul 2023; "2020-10-02" is 10 Feb 2020, which the following "STOP 17/2/20" confirms). It matters most for the three 2025 brivaracetam changes, which are 1, 6 and 10 September 2025, not January, June and October.
- The medication chart header carries an NHS number and the notes name family members. Strip both before any demo, screenshot or upload to Gemini.

## Data analysis findings

Time of day is by far the strongest signal in this diary: 75% of seizures start between midday and 22:00, severe ones peak at 19:00, and that one fact beats everything else in a backtest. Clustering is real but modest, weekly and monthly cycles are weak, and medication changes rarely moved the rate within eight weeks, with one exception the family spotted themselves. All numbers below use the 2,598 dated seizures; "severe" means the carer's H label (head-to-side, slack-jaw, looking-scared and tonic-clonic types, median 2 min), "mild" the L label (quiet-and-aware, aura, absence, median 21 s).

### Baseline

- 2,598 seizures over 2,953 days: 0.88 per day; 55% of days have at least one; 45% of days have none, 33% have one, 15% two, 7% three or more (max 8).
- Median duration 35 s; 22% last 2 min or more; 21 events reached 5 min (the status epilepticus threshold), the most recent a 10-minute one on 11 May 2026.
- Tonic-clonic seizures: 8 in total, none since 9 Jul 2020. The severe type today is a \~2 min focal impaired-awareness seizure.
- The all-seizure rate has climbed since 2023 (0.75 → 0.82 → 1.08 → 1.45 per day in 2026 so far) while the severe rate has stayed flat at about 0.25 per day, so the severe share fell from 36% (2019) to 18% (2026). Either small seizures are increasing or they are being logged more diligently; the diary cannot tell which. That ambiguity is itself an argument for consistent, frictionless logging.

&#91;image: Seizures per month, Jul 2018 to Aug 2026, with the main treatment changes marked\]

### Time of day

- 75% of timed seizures start between 12:00 and 22:00; only 4% start between midnight and 08:00. The 19:00 hour alone holds 281 seizures and 116 of the 791 severe ones (15%). Uniformity is rejected at any significance level.
- The evening peak has sharpened over time: 14:00 to 22:00 held 52% of seizures in 2019 to 2021, 55% in 2022 to 2023 and 78% in 2024 to 2026. The family noticed this ("seizure trend shows more from around 2pm onwards", Jan 2025) and moved brivaracetam doses twice. Those changes were typed as 1, 6 and 10 September 2025 (Excel swapped day and month; January, June and October are wrong), and on the corrected dates the step is unmistakable: in the eight weeks after 1 Sep 2025 the rate went from 5.4 to 10.5 a week (p = 0.0003), and over the following year seizures after 15:00 rose 1.67-fold (18.9 to 31.6 per 30 days) while seizures before 15:00 fell slightly (8.3 to 7.2). Severe seizures rose far less (7.4 to 8.8 per 30 days). This is the strongest medication signal in the diary and it points the same way as the trough idea: with the 14:00 dose gone, the 09:00 brivaracetam (half-life about 9 h) has to cover twelve hours. Two confounders sit on the same date: 1 Sep 2025 was also the first day of the drama-school year, and the period-flag column begins in Aug 2025, which suggests the logging routine changed then. This log cannot separate them; a dose-time log could, and the pattern is worth raising with her team.
- The obvious hypothesis is a pre-dose trough: morning drug levels fall through the afternoon and risk peaks just before the 19:00 cenobamate and 21:00 brivaracetam doses. The family wrote exactly this in Nov 2021 when they split oxcarbazepine into three doses. Only actual dose times can test it, and the diary has none. That is the first thing the app should capture.
- Caveat: seizures during sleep are under-observed, so the overnight 4% is probably an undercount.

&#91;image: Seizures by hour of day, mild and severe stacked, with scheduled medication times marked\]

&#91;image: Share of seizures by hour in 2019–2021 versus 2024–2026\]

### Day of week and longer cycles

- Day of week is a weak effect: Wednesday and Thursday highest (403, 408), Sunday lowest (324); p = 0.04 for all seizures, p = 0.22 for severe. Not worth a feature.
- A Lomb–Scargle periodogram of daily counts peaks at 7.5 and 8.6 days, but the peak sits right at the 95% permutation threshold (power 0.0074 vs 0.0072) and below the 99% line. Autocorrelation shows a small bump at lags 6 to 8 days (0.10 to 0.15) and around 14 to 15 days (0.12). Verdict: a faint weekly rhythm, consistent with the literature on circaseptan cycles, but not strong enough to forecast from on its own. Per-user cycle detection is still worth building because other users will show stronger cycles.
- Menstrual cycle: only 11 period starts are flagged. Days 0 to 3 after a flag average 1.23 seizures per day against 1.43 in the same years, so the flags show no catamenial effect. The notes tell a different story (below).

### Clustering: what today tells you about tomorrow

- The chance of at least one seizure tomorrow is 45% after a seizure-free day, 59% after one seizure, 69% after two and 73% after three or more. Lag-1 autocorrelation of daily counts is 0.23.
- The previous seven days matter more: 0 to 1 seizures in the last week gives a 26% chance of a seizure today (14% severe); 7 or more gives 61% (22% severe).
- The chance of a *severe* seizure tomorrow is flat at 19% to 25% whatever today's count. Clusters are made of small seizures; the big ones are not predicted by counts.
- Within a day: 636 days had two or more seizures; the median gap between them is 3.4 h (interquartile 1.2 to 6.1 h) and 28% of all inter-seizure gaps are under 6 h. On multi-seizure days, a severe first seizure is followed by another severe one 48% of the time, a mild first seizure 34%.
- There is no refractory period after a severe seizure (median 17 h to the next seizure, versus 19 h after a mild one), and the 7-day versus 28-day trend ratio adds nothing: a week that is trending up is not more dangerous than a flat one.

&#91;image: Chance of a seizure tomorrow by today's count, and chance of a seizure today by last week's count\]

### Medication changes

The table compares the 8 weeks before and after each change (seizures per week; p from a Poisson rate test).

| Change | Date | Before /wk | After /wk | Severe before | Severe after | p |
| --- | --- | --- | --- | --- | --- | --- |
| Clobazam tapered 5 → 4 mg | 28 Jan 2019 | 0.5 | 2.75 | 0.5 | 1.12 | <0.001 |
| Clobazam daily dose stopped | 17 Feb 2020 | 4.0 | 5.5 | 1.0 | 1.5 | 0.17 |
| Keto diet started | 20 Jun 2020 | 8.4 | 8.1 | 1.9 | 1.9 | 0.86 |
| Levetiracetam → brivaracetam | 29 Nov 2022 | 7.6 | 5.9 | 2.75 | 2.25 | 0.18 |
| Cenobamate started (12.5 mg) | 17 Feb 2023 | 5.75 | 5.1 | 2.75 | 2.1 | 0.60 |
| Cenobamate reaches 200 mg | 28 Apr 2023 | 5.4 | 4.25 | 2.0 | 1.25 | 0.31 |
| Cenobamate 400 mg | 29 Mar 2024 | 6.6 | 5.0 | 2.0 | 1.6 | 0.18 |
| Oxcarbazepine stopped | 21 Jul 2024 | 5.25 | 6.1 | 1.25 | 1.6 | 0.47 |
| Cenobamate cut to 300 mg | 5 Mar 2025 | 7.0 | 6.9 | 1.75 | 2.25 | 0.93 |
| Brivaracetam re-timed: 100/100/50 (1 Sep), back (6 Sep), 100/0/150 (10 Sep) | 1 Sep 2025 | 5.4 | 10.5 | 1.5 | 3.25 | <0.001 |

- Two changes produced a clear shift: the clobazam taper of Jan 2019 (0.5 to 2.75 a week; the family saw it within days and reversed it) and the brivaracetam re-timing of Sep 2025 (5.4 to 10.5 a week; the rate has stayed up for a year, and the change was made to reduce daytime fatigue, not seizures).
- The cenobamate titration of 2023 shows a gradual improvement that no single 8-week window can prove, but 2023 was the lowest year on record (0.75 per day, 0.25 severe per day).
- The cenobamate cut to 300 mg on 5 Mar 2025 was reversed 11 days later "as seizures increased". The surrounding 8 weeks run at 7.0 and 6.9 per week; the increase they reacted to was within normal week-to-week noise. An app that shows a baseline with its spread would have said so, and that is a more useful feature than a forecast.
- Clobazam rescue doses (188 logged since Apr 2021) are given on bad days: 2.3 seizures that day against 1.5 on other seizure days. The following three days average 2.5 seizures against 3.1 after comparable non-rescue days, which is consistent with cluster-breaking, though regression to the mean explains part of it.
- Missed doses barely exist in this diary (2 notes in 8 years) because a carer gives every dose. The missed-dose signal matters for self-managing adults, not for this user, so demo it with synthetic data.

### What the notes say

786 notes were keyword-scored for themes. The share of severe seizures among noted events is 38%; themes well above that are the carers' strongest candidate triggers.

| Theme in the note | Notes | Severe share |
| --- | --- | --- |
| Period or menstrual | 38 | 63% |
| Travel (car, train) | 46 | 56% |
| Heat, hot shower or bath | 93 | 56% |
| Cold or temperature change | 16 | 50% |
| Exercise or activity | 127 | 48% |
| Food, hunger, keto ratio | 82 | 45% |
| Stress, upset, argument | 67 | 45% |
| School or lesson | 64 | 44% |
| Tired, sleep, late night | 132 | 38% |
| Ill or unwell | 78 | 36% |
| "Felt it coming", aura | 71 | 18% |

- 24 notes name a trigger outright: hot showers (6), heat or a sharp temperature change (5), emotional upset or an argument (7), the stress of school or going out alone (3). Hot showers recur from Dec 2019 to Mar 2021 ("definitely seems that hot showers are a trigger").
- Period mentions carry the highest severe share despite the flag column being empty, so the app should ask about the cycle directly rather than rely on a tick box.
- Prodromes are real for this user: "felt all day that a seizure is about to happen" (Jun 2020), "eyes going funny" (May 2022), "sounds went funny" (several). A one-tap "I feel one coming" entry is cheap and, per the literature, predictive.
- Caveat: carers write notes for memorable seizures, so every theme's severe share is inflated. The ranking is still informative for which fields to add.

&#91;image: Severe-seizure share by what the carer's note mentioned\]

### Risk indicator backtest

A gradient-boosted model was trained on 2019 to 2023 and tested on 2024 to Aug 2026 (970 days, 1,037 seizures) using only things the app would know: hour of day, seizures so far today, counts over the last 24 h, 7 days and 28 days, hours since the last seizure, day of week. Hours were split into three tiers covering 50%, 35% and 15% of the time.

- Any seizure in the next 3 hours: AUC 0.76. High tier hours (15% of the time) are followed by a seizure 25% of the time, low tier hours 3.4%, a 7-fold spread. Hour of day alone scores AUC 0.76; recent history alone 0.55.
- Severe seizure in the next 6 hours: AUC 0.78. High tier 14.7%, low tier 1.9%.
- Any seizure in the next 24 hours: AUC 0.54. A day-ahead forecast is barely better than the base rate for this user.
- A hand-written four-rule score (seizures today, last-week count, time band, under 6 h since the last one) reaches AUC 0.65 for the 3-hour horizon. It loses accuracy against the model but every point of it can be shown to the user, which is the right trade for a health app.

The honest claim is therefore "risk over the next few hours", driven by the clock, what has happened today and the past week. Not "tomorrow", and not "when".

&#91;image: Backtest of the three-tier risk indicator on 2024–2026\]

## Seizure science for app designers

Four facts shape the product: seizure *type* and *duration* decide when to escalate, clusters are common but have no agreed definition, most people have measurable daily and multi-day rhythms, and the big safety risks (status epilepticus, SUDEP) attach to convulsive and night-time seizures rather than to seizure counts.

### Types, in the words a carer would use

| Type | What it looks like | Typical length | Why the app cares |
| --- | --- | --- | --- |
| Focal aware | Stays aware; twitching, odd taste or smell, déjà vu, stomach feeling | seconds to \~3 min | The diary's "quiet and aware" and "deja vu" events; mild, but often the first of a cluster |
| Focal impaired awareness | Dazed, unresponsive, lip-smacking, picking at things; confusion 15 to 30 min after | 30 s to 5 min | The diary's "head to side, saliva, cannot speak"; the severe type here; emergency threshold 10 min |
| Focal to bilateral tonic-clonic | Focal start that spreads into a convulsion | 1 to 3 min | Emergency threshold 5 min; main SUDEP risk |
| Generalised tonic-clonic | Stiffening then jerking, loss of consciousness, possible incontinence; exhaustion for hours | 1 to 3 min | Same; count per year matters for SUDEP risk |
| Absence | 10 to 20 s staring, instant recovery, can recur many times a day | 10 to 20 s | Easy to miss; voice logging after the fact helps |
| Myoclonic, atonic (drop), tonic | Brief jolts; sudden loss of tone with injury risk; stiffening, often in sleep | under 20 s | Injury field matters more than duration |

Source: [Epilepsy Foundation of San Diego seizure types](https://www.epilepsysandiego.org/resources/seizure-types/).

### Clusters

- There is no consensus definition. In use: 3 or more in 24 h (most studies; 14.9% of 4,116 US outpatients met it), 2 or more in 24 h outside the usual pattern, 2 or more in 6 h (rescue-drug trials), 3 or more in 1 h (NICE), and a statistical one: 3 to 4 times the person's own 3-day baseline. [Haut 2022, Epilepsia](https://www.lgsfoundation.org/wp-content/uploads/2021/08/Epilepsia-2022-Haut-Recognizing-seizure-clusters-in-the-community-The-path-to-uniformity-and-individualization-in-1.pdf)
- Among outpatients with more than 4 seizures a year, 71% have clusters, and 37 to 59% of "clusters" found by fixed-count rules could be chance, which is the argument for a per-person baseline definition. [Frontiers in Neurology 2021](https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2021.636045/pdf)
- For this user, a fixed "3 in 24 h" rule fires on 7% of days. A personal rule (today's count above her own 90th percentile) is what the family actually responds to with a clobazam dose.

### Duration thresholds the app should hard-code

- ILAE 2015 status epilepticus timings: tonic-clonic, treat at 5 min, injury likely from 30 min; focal impaired awareness, treat at 10 min, injury likely beyond 60 min; absence, treat at 10 to 15 min. Reaching the second threshold roughly triples 3-month mortality. [Springer summary of ILAE 2015](https://link.springer.com/10.1186/s12883-022-02868-y)
- First-aid rule: call emergency services if a convulsive seizure passes 5 min, a second starts before recovery, consciousness does not return, or it happened in water or with injury. [Epilepsy Foundation MN](https://www.epilepsyfoundationmn.org/wp-content/uploads/2022/07/SSS-Self-Study-Material.pdf)
- Postictal recovery is typically 5 to 30 min; deficits after focal impaired-awareness seizures usually clear within 1 to 2 h. A "recovered at" timestamp is therefore worth logging. [StatPearls](https://www.ncbi.nlm.nih.gov/books/NBK526004/)

### Daily and multi-day rhythms

- Implanted-device data (Baud 2018, 37 patients): every patient had a circadian cycle of epileptiform activity; 73% had a dominant multi-day cycle of 5.5 to 33 days, most often 26 to 30 or 20 to 22 days; seizures clustered on the rising phase. [Baud 2018, Nature Communications](https://pmc.ncbi.nlm.nih.gov/articles/PMC5758806)
- Leguia 2021 (222 patients): circadian seizure cycles in 89%, multi-day in 60% (peaks near 7, 15, 20 and 30 days), yearly in 12%; circadian peaks fall into five phenotypes (around midnight, 03:00, 09:00, 14:00, 18:00). This user's 19:00 peak is the "18:00" phenotype, typical of temporal-lobe onset. [Leguia 2021, JAMA Neurology](https://jamanetwork.com/journals/jamaneurology/article-abstract/2775979)
- The same cycles show up in ordinary diaries: of 1,118 SeizureTracker users with 100+ logged seizures, 80% had circadian modulation, 7 to 21% a weekly cycle and 14 to 22% a cycle longer than three weeks. [Karoly 2018, Lancet Neurology (summary)](https://www.neurologylive.com/view/epileptic-seizure-cycles-found-patient-specific-robust)
- Misconceptions worth avoiding (Karoly 2021): monthly cycles are as common in men as women, so "monthly" does not mean hormonal; short diaries fake weekly and menstrual links (one 35-seizure link vanished at 245 seizures); drug half-lives are too short to create multi-day rhythms. [Karoly 2021, Frontiers in Neurology](https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2021.720328/full)
- Data needed before claiming a cycle: diary studies used 30 to 100 seizures; Seer's forecaster starts at 10 to 20 logged seizures and improves with length. The app should show "not enough data yet" below about 30 events.

### SUDEP, the risk that is not about counts

- Adult incidence is about 1.2 per 1,000 patient-years; three or more tonic-clonic seizures a year raises relative risk around 15-fold; nocturnal seizures and being untreated add to it, and sharing a bedroom lowers it. [AAN guideline](https://www.aan.com/Guidelines/home/GetGuidelineContent/852)
- Swedish case-control (255 SUDEP cases): a tonic-clonic seizure in the previous year gave roughly 27 times the risk; non-convulsive seizures alone gave no excess; nocturnal convulsions about 15 times; living alone about 5 times; convulsions plus sleeping alone, odds ratio 67. [CURE Epilepsy summary](https://www.cureepilepsy.org/news/clinical-risk-factors-in-sudep-a-nationwide-population-based-case-control-study/)
- Implication: the app should count convulsive seizures per year and night-time seizures as a separate, prominent number for the user and clinician, and never fold them into a generic score where they would be swamped by small events. This user has had none since 2020, which is a reassuring figure the app should be able to display.

## Triggers and trackable factors: what the evidence says

The factors with real evidence are the person's own warning signs, stress, missed doses, sleep *timing* and (for about a third of women) the menstrual cycle. Heat and weather are plausible but the studies contradict each other, so treat them as optional overlays. Ranked by how much weight the risk logic should give them:

| Factor | Evidence | Effect size | How to capture it |
| --- | --- | --- | --- |
| "I feel one coming" / premonitory symptoms | Haut 2007 (71 adults, 15,635 days): a positive 24 h self-prediction doubled the odds; Haut 2012 e-diary: blurred vision OR 18, light sensitivity OR 8, each extra symptom +24%; "almost certain" OR 9 at 6 h | Largest of any factor; sensitivity \~50%, specificity \~95% in good predictors | One-tap or one-phrase entry; Gemini asks "anything feel off?" at check-in. [Haut 2007](https://www.aan.com/PressRoom/home/PressRelease/433) · [Haut 2012](https://pubmed.ncbi.nlm.nih.gov/22424857) |
| Time since last seizure, today's count | Clusters affect 71% of people with frequent seizures; risk is elevated right after a seizure | This diary: 45% → 73% chance tomorrow by today's count | Automatic from the log. [Frontiers 2021](https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2021.636045/pdf) |
| Missed or late doses | RANSOM (33,658 patients): non-adherence tripled death risk; Uganda cohort: >3 missed doses a week raised breakthrough seizures from 73% to 92% | Strong, but only for people who self-manage | Log actual dose time; urgency scaled to half-life (brivaracetam 7 to 8 h, levetiracetam 6 to 8 h, clobazam 10 to 30 h plus a 36 to 46 h metabolite, lamotrigine 15 to 35 h). [RANSOM](https://sciencedaily.com/releases/2008/06/080618161549.htm) · [ILAE TDM guideline](https://discovery-pp.ucl.ac.uk/id/eprint/10049571/1/Patsalos%20Patsalos%20et%20al%202018-AED%20%20TDM-Manuscript-Revision%201-24_05_18-FINAL.pdf) |
| Stress | 82% of 266 patients name it; prospective diary (64 adults): each 3-point rise on a 0 to 10 scale raised next-day odds 32%, but significant within-person in only 20 to 25% | Moderate at group level, real for a minority | Daily 0 to 10 rating; only surface it for a user once their own data support it. [Privitera](https://www.uc.edu/news/articles/legacy/healthnews/2014/10/study-sheds-light-on-epilepsy-and-stress.html) · [Haut diary](https://aesnet.org/abstractslisting/stress-is-associated-with-an-increased-risk-of-seizures-in-persons-with-epilepsy--results-of-a-diary-study) |
| Sleep timing (not hours) | Fitbit study, 60 patients, 30,485 nights (Brain 2023): shifted bed or wake times preceded seizures in 14 of 34, sleep duration in only 5 of 34; nocturnal seizures raised 48 h risk | Timing matters, duration mostly does not | Bed and wake times from the watch; flag nocturnal seizures separately. [Seer summary](https://seermedical.com/research/sleep-and-seizure-risk-in-epilepsy-bed-and-wake-times-are-more-important-than-sleep-duration) |
| Menstrual cycle | About one third of women meet the 2-fold "catamenial" rule; perimenstrual (days -3 to +3) commonest; self-report does not predict who has it | Strong where present | Ask cycle day; test for a 2-fold phase rise after several cycles. [AES abstract](https://aesnet.org/abstractslisting/catamenial-epilepsy-prevalence-and-patterns-in-a-mixed-epilepsy-population) |
| Alcohol | 18% of drinkers had alcohol-related seizures, all after 7+ drinks, 95% within 12 h of stopping | Threshold effect | Log drinks; only heavy sessions matter. [Frontiers 2018](https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2018.00401/full) |
| Heat and weather | UCL intracranial study (9 patients): more seizures in heatwaves; Jena (604 admissions): falling pressure +14% per 10 hPa, humidity >80% up to +48%, warm days *halved* risk; Spain 2025 (4,755 admissions): cold raised admissions, heat lowered them | Direction inconsistent across studies | Optional overlay from weather API; this user's notes point to hot showers and sharp temperature changes rather than weather. [UCL](https://www.ucl.ac.uk/news/2024/sep/heatwaves-may-increase-likelihood-seizures-people-epilepsy) · [Rakers 2017](https://idw-online.de/de/news675088) · [Spain 2025](https://www.frontiersin.org/journals/public-health/articles/10.3389/fpubh.2025.1708538/full) |
| Flashing lights | \~3% of people with epilepsy; 16 to 25 Hz most provocative | Rare | Yes/no in profile, not a daily field. [Epilepsy Society](https://epilepsysociety.org.uk/sites/default/files/2025-04/PhotosensitiveepilepsyApril2025.pdf) |
| Illness, fever, dehydration, low blood sugar, caffeine | On every foundation trigger list; adult evidence is case reports and animal data | Unquantified | Free-text or a "feeling unwell" toggle. [Epilepsy Foundation AU](https://epilepsyfoundation.org.au/understanding-epilepsy/seizures/seizure-triggers/) |

Two cautions from the literature. Survey studies find 53 to 97% of patients name at least one trigger, with stress, sleep loss and tiredness always on top, but when the same people keep prospective diaries most named triggers do not predict their seizures; in one randomised dataset self-rated likelihood helped and reported precipitants added nothing. [Nakken 2005](https://pubmed.ncbi.nlm.nih.gov/15652738/) · [AAN abstract](https://www.aan.com/MSA/Public/Events/AbstractDetails/41994). So the app should collect triggers to *test* them per person, and show a trigger as "yours" only when the person's own log supports it.

### Forecasting from diaries: the honest record

- Cycle-based diary forecasts (33 Seer users, 30+ seizures each): 64.5% of seizures fell in high-risk time that covered 16.6% of the clock, mean AUC 0.85 retrospectively; but diary-built forecasts checked against implanted EEG beat chance in only 4 of 8 people. [Karoly 2020](https://www.medrxiv.org/content/10.1101/2019.12.19.19015453.full.pdf)
- Seer's prospective validation (460 users, 6 months; forecasts from 10 seizures, updated weekly): 95% above chance, mean AUC 0.67 to 0.69, sensitivity \~50%, specificity \~75%. Only 40% of users judged the forecast useful; "feeling more in control" was the commonest benefit. [AES abstract](https://aesnet.org/abstractslisting/prospective-validation-of-a-mobile-and-wearable-app-to-forecast-seizure-risk) · [user experience](https://seermedical.com/research/user-experience-of-a-seizure-risk-forecasting-app)
- Goldenholz's group: a deep model on 6,803 diaries beat a rate-matched random forecaster retrospectively (AUC 0.87 vs 0.83) but prospectively tied a plain trailing 84-day moving average (AUC 0.82 both). Chang 2025 (5,501 diaries): none of five models, including a cycle model, beat the moving average, and day-ahead diary-only forecasting "may be infeasible". [Goldenholz prospective](https://www.medrxiv.org/content/10.1101/2024.01.11.24301175v1.full.pdf) · [Chang 2025](https://research.bidmc.org/daniel-goldenholz/publications/rigorous-evaluation-five-models-e-diary-only-seizure-forecasting-retrospective-and)
- Fitbit heart rate plus diary (11 users): retrospective AUC 0.74 hourly, pseudo-prospective 0.68. [Stirling 2021](https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2021.704060/full)

This matches the backtest on your own data exactly: hours-ahead risk from the clock and recent events is defensible (AUC \~0.76); day-ahead forecasting is not. Benchmark whatever you build against a trailing 90-day average and, if it cannot beat that, show the average.

## Wearables and heart rate: what Apple-Watch-style data can and can't do

Consumer watch data is good for three things: detecting convulsive seizures (with a cleared, on-device app), giving honest bed and wake times, and feeding slow daily or weekly rhythm features into a risk level. It is not good for detecting this user's seizures (which are mostly brief, non-convulsive and happen awake) or for minutes-ahead warning, and HealthKit does not deliver data fast enough to try.

### What the heart actually does during a seizure

- About 82% of patients show a significant heart-rate rise during seizures (64% of generalised, 71% of focal seizures), mostly temporal-lobe data; the rise typically begins within 30 s of onset and peaks within a minute, usually 30+ bpm or 50% over baseline. [Eggleston 2014](https://stanfordhealthcare.org/publications/326/326814.html) · [2021 review](https://pmc.ncbi.nlm.nih.gov/articles/PMC7994524)
- In 145 recorded seizures, tachycardia preceded EEG onset by a mean of 13.7 s in temporal-lobe seizures; strict definitions (100+ bpm and a 35 bpm or 55% rise) are met by about half of patients and 44% of their seizures. [Leutmezer 2003](https://Sudepwiki.Pathology.Jhmi.edu/index.php/Electrocardiographic_changes_at_the_onset_of_epileptic_seizures) · [AES abstract](https://aesnet.org/abstractslisting/quantification-of-ictal-tachycardia-prevalence-in-an-epileptic-patient-population)
- Wrist PPG caught only 60% of ECG-confirmed ictal tachycardias (47% of non-motor seizures) and lagged EEG onset by about 14 s; movement wrecked the signal in the misses. [PPG study](https://pmc.ncbi.nlm.nih.gov/articles/PMC8470979)
- ILAE/IFCN 2021 recommends wearable detection only for convulsive seizures with validated accelerometer, EMG or accelerometer-plus-heart-rate devices (sensitivity 90 to 96%, 0.2 to 0.67 false alarms a day); heart-rate detection of non-convulsive seizures produced up to 43 to 50 false alarms a day and is not recommended. [ILAE guideline](https://ilae.org/files/ilaeGuideline/Automjated-seizure-detection-using-wearable-devices---epi.16818.pdf)

### HRV as an early warning

- A scoping review of 72 studies finds pre-ictal HRV changes 2 to 40 min before onset (SDNN and Poincaré indices), almost all offline in monitoring units, feasible outside hospital only for people with strong autonomic changes, with no way yet to identify who those are. [MDPI review](https://www.mdpi.com/2077-0383/13/3/747)
- The best small studies report 89 to 94% sensitivity with 0.5 to 3.4 false positives an hour; a 2023 wearable-ECG study managed 64% sensitivity at 0.69 false positives an hour. Hours of false alarms a day is not a product. [Pavei 2017](https://eprints.whiterose.ac.uk/124542/) · [Billeci 2018](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0204339)

### What the watch gives you, at what rate

| Signal (Apple HealthKit) | Resolution | Useful for |
| --- | --- | --- |
| Background heart rate | \~1 reading per 5 min while still; every 5 s only in workouts (Series 12 and Ultra 4 from Sept 2026 do 5 s all day, but background delivery to apps is capped at hourly) | Daily resting and night-time HR for slow cycles; a 10-minute snapshot attached to a logged seizure |
| HRV (SDNN) | Every 4 h by default, 15 min with AFib History on; RMSSD added in iOS 27 | Daily trend only; label experimental |
| Resting HR, walking HR | One value a day | Weekly cycle features |
| Sleep stages | 30-s epochs, accelerometer-only, kappa 0.63 to 0.68 vs polysomnography | Bed and wake times (the signal that matters), rough duration |
| Wrist temperature | One nightly deviation from a 5-night baseline, needs 4 h of Sleep Focus | Slow cycles; menstrual-phase proxy |
| Respiratory rate | Nightly range | Little |

Sources: [Apple heart-rate white paper](https://apple.com.cn/health/pdf/Heart_Rate_Calorimetry_Activity_on_Apple_Watch_November_2024.pdf) · [5-second HR note](https://blakecrosley.com/blog/five-second-heart-rate-healthkit) · [wrist temperature](https://support.apple.com/en-us/HT213275) · [sleep stages](https://www.apple.com/kr/health/pdf/Estimating_Sleep_Stages_from_Apple_Watch_Oct_2025.pdf)

### Evidence that watch data helps a risk level

- Multi-day heart-rate cycles existed in all 46 people in a Seer study (weekly in 54%, monthly in 28%) and seizures phase-locked to them in 10 of 19; combining diary cycles with heart-rate cycles gave prospective AUC 0.77. [cycles study](https://doaj.org/article/91bae446e9d449acbb108531abdeecb8) · [prospective pilot](https://seermedical.com/research/forecasting-seizure-likelihood-from-cycles-of-self-reported-events-and-heart-rate-a-prospective-pilot-study)
- Fitbit sleep in 44 adults over 13 months: oversleeping raised 48-h seizure odds (OR 1.20); undersleeping had no group effect; bed and wake-time shifts mattered for 11 of 29 people, in individual directions; night-time seizures raised next-day risk in 19 of 21. [medRxiv](https://www.medrxiv.org/content/10.1101/2022.08.05.22278453.full.pdf)
- Mayo's wearable forecasting (Empatica E4 against implanted ground truth, 6 patients): forecasts beat chance in 5 of 6 with about 33 min lead, and time of day was the strongest feature, ahead of motion, skin conductance and temperature. [Physics World summary](https://physicsworld.com/a/wearable-device-provides-advance-warning-of-epileptic-seizures/)

### What this means for your app

- Position the watch as "detects the big ones (via a cleared app) and knows when you slept", never as prediction. For this user it would detect almost nothing: 8 convulsive seizures in 8 years, none since 2020.
- Use HealthKit for three derived features per day: resting HR, bed time, wake time. Feed them to the cycle analysis in section 9 and show them as overlays; nothing faster is honest.
- If the demo needs a live heart-rate moment, copy EpiWatch's pattern: a HELP or "just had one" tap snapshots the last 10 minutes of HR and motion and attaches it to the record. That is real, cheap, and clinically meaningful (ictal HR rise is a useful fact for the neurologist).
- Users of cleared detectors expect 90%+ sensitivity and one or two false alarms a month; do not ship a home-made detector that cannot meet that. [user preferences review](https://dannydid.org/wp-content/uploads/Epilepsia-2025-Hadady-Users-perspectives-and-preferences-on-using-wearables-in-epilepsy-A-critical-review.pdf)

## Existing tracking and prediction tools

Nobody has shipped a voice-first seizure diary with evidence behind it, cleared detectors only cover convulsive seizures, and the one consumer forecasting product (Seer) sold itself as a weather forecast, trained from 10 logged seizures, and found that only 40% of users trusted it. That is the gap and the bar.

| Tool | What it does | Inputs | Output | Status and evidence |
| --- | --- | --- | --- | --- |
| [Seer app](https://seermedical.com/wp-content/uploads/SeerHealth_FAQs-SHFAQ-AU-001.pdf) (Seer Medical, Melbourne) | Diary plus cycle-based seizure risk forecast | Logged seizure times, meds; optional Fitbit heart rate | 0 to 1 likelihood binned low / medium / high; 24 h and long-range view; recomputed weekly and after each seizure | Wellness product, not a device; prospective validation 460 users: 95% above chance, AUC 0.67 to 0.69, sensitivity 52%, specificity 75%; company entered administration Dec 2024, rescued Apr 2025 by Cadwell, app future unstated ([validation](https://aesnet.org/abstractslisting/prospective-validation-of-a-mobile-and-wearable-app-to-forecast-seizure-risk), [rescue](https://www.smartcompany.com.au/startupsmart/seer-medical-40-million-rescue-deal-breakthrough-victoria-cadwell/)) |
| [Empatica EpiMonitor](https://fda.innolitics.com/device/K250515) (EmbracePlus) | Detects convulsive seizures, alerts carers | Wrist EDA, accelerometer, skin temperature | Call plus SMS to carers, repeat until answered, 15 s cancel; diary of seizures, sleep, activity | FDA cleared Jun 2025, ages 6+; real-world 1,444 users: sensitivity 80 to 87%, 0.25 to 0.34 false alarms a day; AES 2025: 103 of 107 convulsive seizures caught ([AES](https://aesnet.org/abstractslisting/real-world-performance-of-an-fda-cleared-seizure-detector-using-a-next-generation-accelerometer-and-electrodermal-activity-based-wristband)) |
| [EpiWatch](https://fda.innolitics.com/device/K243515) (Johns Hopkins spin-out) | Convulsive seizure detection on Apple Watch | Watch accelerometer and heart rate, on-device | Call, text, email with GPS; HELP button; med reminders, trigger insights, logging | FDA cleared Mar 2025, prescription only, US only, subscription; 242-subject study: 46 of 47 seizures, one false alarm per 12 days; standalone cellular watch since Mar 2026 ([App Store](https://apppricinglab.com/app/apple/6751776471)) |
| [NightWatch](https://fda.innolitics.com/device/K243199) (LivAssured) | Night-time major motor seizure detection | Upper-arm PPG heart rate plus accelerometer, bedside base station | Alarm to carer, data portal | FDA cleared Jul 2025 for ages 4 to 16; 53 children, 2,310 nights: 89% sensitivity, 0.06 false alarms an hour; carer strain fell significantly ([Epilepsia 2023](https://researchinformation.umcutrecht.nl/en/publications/multimodal-nocturnal-seizure-detection-in-children-with-epilepsy-/)) |
| [SeizureTracker](https://www.ninds.nih.gov/sites/default/files/migrate-documents/icare_seizuretracker2019b_508c.pdf) | Free diary, 24,000+ users, 2.3 M events | Timer plus video in one tap; triggers, rescue meds, VNS swipes added later; Alexa voice logging | Graphs, exports; data feeds research (Karoly cycles paper, Goldenholz) | Volunteer-run; the research-grade diary; no forecast |
| [Epsy](https://www.digitalhealthhub.org/award-finalists/EWdaBvMO) (LivaNova-affiliated) | Polished consumer diary | Seizures, auras, side effects, triggers, mood, meds with reminders; HealthKit HR and activity; Apple Watch quick log | Calendar and timeline, insights after a week, doctor-ready PDF, clinician hub | 100k+ downloads, 4.75 stars; recurring complaints: no duration field, no custom triggers, watch logging breaks ([reviews](https://splitmetrics.com/apps/epsy-seizure-log-for-epilepsy/id1479108189)) |
| [Epilepsy Foundation My Seizure Diary](https://www.epilepsy.com/tools-resources/my-seizure-diary) | Printable and app diary | Date, time, duration, type, aura, recovery, triggers, missed doses, rescue meds, mood, hormonal changes | Summary for clinic | The field list is a good checklist; a clinician review found one diary app hid seizure-free days and misled doctors ([AES](https://aesnet.org/abstractslisting/self-management-in-epilepsy--web-based-seizure-tracking-applications)) |
| NeuroPace RNS | Implanted responsive stimulator | Intracranial EEG | Research source of the multi-day cycle findings | Not a comparator; it is where the cycle science comes from ([Baud 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC5758806)) |

### Apple Watch itself and the AI diary space

- Apple ships no seizure feature; the watch is a wellness device in every epilepsy charity's product list. Unvalidated subscription apps (SeizAlarm, EpiCentr, Inspyre, EpiPal) use motion plus heart rate with no clearance. [Apple support](https://support.apple.com/en-us/120277) · [Calgary device review](https://cumming.ucalgary.ca/sites/default/files/teams/334/Epilepsy%20Monitoring%20Devices_Completed_Netanya%20Winterburn_Aug%2021%202025.pdf)
- Samsung Galaxy Watch research (36 adults, 2024): random-forest detection of convulsive seizures, sensitivity 0.87, 0.21 to 0.28 false alarms a day; heart-rate features beat motion features. [UTMB](https://researchexperts.utmb.edu/en/publications/reliable-detection-of-generalized-convulsive-seizures-using-an-of/)
- No shipped LLM or voice seizure diary with published evidence exists; the closest is SeizureTracker's Alexa command. LLM extraction from clinic text reaches F1 0.76 to 0.80 for seizure and epilepsy type and 0.92 for current drugs, below epileptologists, which is why a confirm-before-save step matters. [PMC 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12455391)
- Free text matters: in EpiDiary (42,799 users), 2,423 cluster patients were visible only in notes, never in structured fields. Your diary shows the same: the trigger signal lives in the notes. [Stanford](https://stanfordhealthcare.org/publications/797/797184.html)

### What to copy and what to avoid

- Copy from SeizureTracker: timer and video in one tap, details edited afterwards. Copy from Epsy: calendar plus timeline, a doctor-ready PDF, adherence trends. Copy from Seer: the forecast as a weather-style likelihood with an explicit cold-start state and the "feel more in control" framing.
- Avoid Epsy's missing duration field, any diary that hides seizure-free days, and any claim of detection from HealthKit data.
- Carry the three disclaimers every cleared or wellness product uses: not a medical device; cannot detect seizures; for people with diagnosed epilepsy, for discussion with their clinician.

## Recommended logging schema

Log four kinds of record (seizure, dose, check-in, wearable sample), keep every field optional except a timestamp, and let Gemini fill gaps by asking one question at a time. The schema below is what the analysis in section 3 and the evidence in section 5 actually use; everything else is noise.

### Seizure event

| Field | Type | Why | Gemini follow-up if missing |
| --- | --- | --- | --- |
| `start_time` | datetime | Everything (time-of-day, clustering) keys off it | "Roughly when did it start?" (accept "about ten minutes ago") |
| `duration_s` | int, or `estimated: true` | Status thresholds, severity; the diary shows carers often guess | "How long did it last, even roughly?" |
| `type` | enum: aware, staring, impaired\_awareness, convulsive, drop, jerk, unsure | Severity label; SUDEP counting of convulsive events | "Was she aware during it? Any shaking or stiffening?" |
| `awareness` | enum: kept, impaired, lost | Separates the diary's L from H types | folded into the type question |
| `asleep_at_onset` | bool | Nocturnal seizures carry 48 h and SUDEP risk | "Was she asleep when it started?" |
| `recovered_at` | datetime | Postictal length; a second seizure before recovery is an emergency | "Is she back to normal yet?" |
| `injury`, `incontinence` | bool | Clinical review and drop seizures | only if type suggests it |
| `rescue_med` | drug + dose + time | Cluster-breaking analysis (188 clobazam doses in this diary) | "Did you give any clobazam?" |
| `warning_before` | bool + free text | Prodromes predict with OR 3 to 18 | "Did she feel it coming?" |
| `context` | free text, plus tags: shower/bath, hot, cold, exercise, travel, upset, school, unwell, period, hungry | The themes that separate severe from mild in 786 notes | "What was she doing just before?" |
| `who_logged`, `confidence` | enum | Carer vs patient vs watch; "GUESS" entries exist in the diary | automatic |

### Medication dose

`drug`, `dose_mg`, `scheduled_time`, `taken_time`, `skipped: bool`, `reason`. The single most valuable new field is `taken_time`; the diary has eight years of schedules and zero actual times. From it the app derives *hours since last dose* and *late by N minutes*, and can finally test the pre-dose trough hypothesis.

### Daily check-in (voice, 30 seconds, ideally morning)

`sleep_bed_time`, `sleep_wake_time` (timing beats hours), `sleep_quality` 1 to 5, `stress` 0 to 10, `mood` 0 to 10, `feeling_off: bool` (the premonitory flag), `unwell: bool`, `cycle_day` or `period_started: bool`, `alcohol_units`, `exercise: bool`, `notes`. Gemini should ask only what is blank and stop after two questions; a check-in that takes a minute will not happen on day 40.

### Wearable sample (if a watch is paired)

`heart_rate` (HealthKit gives roughly one sample every few minutes at rest, every second during workouts), `hrv_sdnn` (a few readings a day), `resting_hr`, `sleep_stages`, `wrist_temperature` (nightly), `steps`. Store raw, resample to 5-minute bins. Section 6 says what each is good for.

### Profile

Seizure types the person has, usual regimen (drug, dose, times), half-life class per drug for the lateness logic, emergency plan (rescue med, 5 or 10 minute rule, who to call), whether they sleep alone, photosensitivity yes/no, menstruating yes/no.

### Voice-capture rules for the system prompt

- Ask one question at a time, never more than three per entry, starting with start time and duration.
- Accept vague answers and store them with `estimated: true` rather than pushing for precision.
- Repeat back the record in one sentence before saving ("Logged: 19:15, about 90 seconds, head to the side, just after a hot shower. Right?").
- Never offer dosing advice; if asked, say to contact the epilepsy nurse and offer to note the question for the clinician.
- If duration is still running and passes 5 minutes for a convulsive seizure, or 10 minutes otherwise, stop logging and read the emergency plan.
- Use the drug names from the profile as custom vocabulary so "cenobamate" is not transcribed as "send a bomb mate".

## Risk score design

Build "risk over the next few hours" as a transparent points score that is calibrated per person, shown with its reasons, and kept apart from the hard safety rules. Call it a risk *level*, never a prediction. On your data this design separates high-tier hours (25% chance of a seizure within 3 h) from low-tier hours (3.4%) and a four-rule version of it still reaches AUC 0.65.

### Components and weights

| Component | Points | Why this weight | Needs |
| --- | --- | --- | --- |
| Time-of-day band from the person's own histogram | 0 to 2 (current hour's share vs a flat day: >2× flat = 2, >1× = 1) | Strongest signal in the diary (AUC 0.76 alone); Leguia: 89% of people have a circadian cycle | 30+ events; before that, flat |
| Seizures so far today | 0 / 1 / 2 for 0 / 1 / 2+ | 45% → 59% → 69% chance tomorrow; median same-day gap 3.4 h | nothing |
| Hours since last seizure | +0.5 if under 6 h | 28% of inter-seizure gaps are under 6 h | nothing |
| Last 7 days vs the person's 90-day baseline | +1 above 75th percentile, +0.5 above median | 26% vs 61% chance of a seizure today by last-week count | 4+ weeks |
| Dose late or missed | +1 if overdue by more than ¼ of the drug's half-life, +2 if a dose was skipped | Literature only (no missed doses in this diary); brivaracetam and levetiracetam run out in hours | dose log |
| "Feeling off" or warning symptom logged in the last 6 h | +2 | OR 3 to 18 in e-diary studies, the largest effect anywhere | check-in |
| Stress 7+ today | +0.5, only once the person's own data show the link | OR 1.32 per 3 points at group level, real for 20 to 25% of people | 8+ weeks |
| Multi-day cycle rising phase | +0.5 once a cycle is significant | 60% of people have one; this user's is faint | 30+ events, permutation test |
| Period day -3 to +3 (if tracked) | +0.5 once a 2-fold phase rise is seen | One third of women; 63% severe share in this diary's period notes | 3+ cycles |

### From points to a tier

- Compute the score hourly. Set the thresholds per person so that over the trailing 90 days "high" covers about 15% of hours and "low" about 50%. Fixed thresholds would make a person with daily seizures permanently "high", which is useless.
- Show the tier with its reasons in plain words: "High: it's 7 pm, your busiest hour (18% of your seizures); two seizures already today; evening dose not yet logged."
- Show what it is not: one line under the tier, "This is a pattern from your own diary, not a prediction. Low never means safe."
- Benchmark: every month, compare the score against a trailing 90-day average on the person's own log (AUC and Brier). If it does not beat the average, show the average instead. Goldenholz's group found that most published diary models fail this test.
- Start cold honestly: with fewer than 30 events, show only today's count and time since last seizure, labelled "learning your pattern".

### Safety rules that bypass the score

- Running timer passes 5 min (convulsive) or 10 min (other): full-screen emergency plan, offer to call. ILAE status thresholds.
- Second seizure before recovery from the first: same.
- Cluster alert: today's count exceeds the person's own 90th percentile, or 3 in 24 h, or 2 in 6 h: prompt the rescue plan and suggest logging whether a rescue dose was given.
- Separate counters, always visible to carer and clinician, never blended into the tier: convulsive seizures in the last 12 months, night-time seizures in the last 30 days. These are the SUDEP numbers.

### Why not let Argon produce the number

A language model asked to "estimate risk" will produce a fluent number with no calibration and no audit trail. Use Argon to explain the computed tier, summarise the week, and propose questions for the clinic; keep the arithmetic in code you can test against the backtest in section 3.

## Demo plan from the existing data

The eight-year diary lets you demo every feature on real history rather than on a toy dataset, which is rare at a hackathon. Six demos, in the order a judge would want to see them; the first three are the core.

1. **Voice logging with follow-up.** Carer, in one breath: "She had one about quarter past seven, maybe a minute and a half, her head went to the side, she'd just got out of the shower." Gemini Live asks one thing: "Had she taken her 7 pm cenobamate yet?" The JSON record appears on screen as it is spoken; the "hot shower" trigger tally ticks up; the risk tier updates. This is the whole product in 40 seconds.
2. **Eight years in eight seconds.** Import the anonymised diary (strip names and the NHS number first) and render the hour-of-day histogram, the monthly timeline with treatment changes, and the cluster statistics. Say the one sentence: "75% of her seizures happen between midday and 10 pm, peaking at 7 pm, right before her evening dose."
3. **"Risk now" replay.** Scrub through a real day hour by hour and watch the tier move with its reasons. Good days to pick: 29 Jan 2019 (three severe seizures in a day after a clobazam taper, which the score flags from 12:30), or any 2026 evening where the tier climbs from medium at 14:00 to high at 18:00. Close with the backtest chart: high-tier hours 25%, low-tier 3.4%.
4. **The baseline that would have changed a decision.** Show the week of 5 Mar 2025: cenobamate cut to 300 mg, reversed 11 days later because seizures "increased". The app shows that week's count against her 90-day range and says "within your usual range". Then show Jan 2019, where the app would have flagged a 5-fold rise within 48 h of a dose change. Same feature, two opposite and correct answers.
5. **Trigger discovery from free text.** Feed the 786 notes to Argon with the schema in section 8 and show the extracted tags, then the table from section 3: heat and showers 56% severe, periods 63%, travel 56%. End with the app's wording: "Hot showers appear in 93 of your notes and those seizures were more often the severe kind. Worth raising with your nurse."
6. **Weekly read-back.** Argon writes the week's summary JSON; Gemini Live reads it aloud: "Nine seizures this week, two severe, both after 6 pm; your evening doses were logged on time every day; no night-time seizures."

What has to be synthetic, and should be labelled as such on the slide: missed-dose scenarios (the diary has none) and smartwatch heart-rate traces (none in the data). Generate a fake week with one skipped brivaracetam dose and show the tier responding; do not pretend it came from the diary.

Preparation checklist:

- [ ] Export the Seizure Data tab to CSV with the type labels normalised (section 2 lists the variants) and the 44 undated rows removed
- [ ] Replace every personal name in notes with a role word ("mum", "brother", "nurse") and delete the NHS number from the medication chart before anything is uploaded to Gemini
- [ ] Build the medication timeline table by hand from Meds Changes and Current (watch the day/month swaps noted in section 2)
- [ ] Pre-compute the per-hour histogram, 90-day baselines and tier thresholds so the replay is instant
- [ ] Record a fallback video of the voice demo in case the venue Wi-Fi fails the WebSocket

## Gemini build notes

Use `gemini-3.8-live` for the voice front end and `gemini-4-argon` for the analysis layer; nothing else in the lineup does both, and "Jev" is not a Google model at all. Facts below were checked against the live Google docs on 31 Oct 2026.

### Which model for what

| Job | Model ID | Why | Watch out |
| --- | --- | --- | --- |
| Voice logging with follow-up questions | `gemini-3.8-live` | Default Live API model, GA 15 Sep 2026; native audio in and out, barge-in, function calling while it keeps talking | Audio-only output (get text via transcription); no structured output; 128k context; free tier exists |
| Post-session extraction to JSON | `gemini-3.8-flash` | Cheap, GA, free tier, `response_format` with a JSON schema, 1M context | Schema keywords like `minLength` are silently ignored; validate in Pydantic/Zod |
| Trend analysis, risk explanation, chart generation | `gemini-4-argon` | GA 13 Oct 2026, 1M context, code execution (pandas, matplotlib, scikit-learn in a sandbox), structured output, function calling | Paid tier only (someone must enable billing, $2/$10 per 1M tokens until 30 Nov then $4/$20); not in the Live API; hard prompts can take minutes |
| Fallback for analysis if billing is a problem | `gemini-3.8-flash` | Same tools, free tier | Less capable reasoning |

"Jev" (JevOne) is TypeSafe AI's "System One" model: it returns calibrated probabilities for yes/no or multiple-choice questions, generates no text, sits behind a waitlist, and would break the DeepMind-model rule. Do not pick it. [Gemini models](https://ai.google.dev/gemini-api/docs/models) · [Gemini 4 Argon](https://ai.google.dev/gemini-api/docs/models/gemini-4-argon) · [3.8 Live](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live) · [pricing](https://ai.google.dev/gemini-api/docs/pricing) · [Jev](https://gigazine.net/gsc_news/en/20260916-system-one-jev)

### Live API specifics that matter for this app

- Transport is a stateful WebSocket; the browser should connect with an ephemeral token minted by your backend (`client.auth_tokens.create`, `uses: 1`, locked to `gemini-3.8-live`), never a raw API key. [ephemeral tokens](https://ai.google.dev/gemini-api/docs/live-api/ephemeral-tokens)
- Send 16-bit PCM at 16 kHz in 20 to 100 ms chunks; playback is 24 kHz PCM. Turn on `input_audio_transcription` and `output_audio_transcription` and give the input transcription a `custom_vocabulary` of the user's drug names (brivaracetam, cenobamate, clobazam) and seizure words; this is the single biggest accuracy win for medical vocabulary. [capabilities](https://ai.google.dev/gemini-api/docs/live-api/capabilities)
- Function calling is `NON_BLOCKING` by default on 3.8 Live, so the model can keep talking while `log_seizure(...)` runs; you must send `send_tool_response` yourself. User barge-in cancels pending calls (`toolCallCancellation`). Keep tools few and flat; the docs say the model performs best with single calls. [tools](https://ai.google.dev/gemini-api/docs/live-api/tools)
- Sessions: 15 min of audio-only without compression and about 10 min per connection; set `context_window_compression: {sliding_window: {}}` and `session_resumption: {}` and handle `goAway`. [session management](https://ai.google.dev/gemini-api/docs/live-api/session-management)
- Proactive audio is permanently on for 3.8 Live; affective dialog has been removed from that model, so do not build on it. Omit `thinking_level` on `gemini-3.8-live` (it errors); `gemini-3.8-live-extended-thinking` exists if you want the model to reason before answering a hard question, at the cost of latency.
- Structured output is not supported inside Live. The reliable pattern is: capture facts through typed function-call arguments during the conversation, then run one `gemini-3.8-flash` call over the full two-sided transcript with a JSON schema to produce the canonical record and catch anything the model said back but never logged.
- The docs now centre on the Interactions API (`client.interactions.create`, `google-genai` ≥ 2.3.0); `generateContent` still works and is marked legacy. [Interactions](https://ai.google.dev/gemini-api/docs/interactions)

Minimal session shape (Python, from the quickstart):

```python
from google import genai
from google.genai import types
client = genai.Client(api_key=KEY)
config = {
  "response_modalities": ["AUDIO"],
  "system_instruction": DIARY_PROMPT,   # persona, one follow-up per missing field, never dosing advice
  "input_audio_transcription": {"custom_vocabulary": DRUG_AND_SEIZURE_TERMS},
  "output_audio_transcription": {},
  "tools": [{"function_declarations": [log_seizure, log_dose, log_symptom, get_todays_meds]}],
  "context_window_compression": {"sliding_window": {}},
  "session_resumption": {},
}
async with client.aio.live.connect(model="gemini-3.8-live", config=config) as s:
    await s.send_realtime_input(audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000"))
    async for msg in s.receive():
        if msg.server_content and msg.server_content.model_turn: ...        # play audio parts
        if msg.server_content and msg.server_content.input_transcription: ...  # user text
        if msg.tool_call: await s.send_tool_response(function_responses=[...])
```

### The analysis call

- Put months of diary rows (CSV or JSON) straight into one Argon prompt; 1M tokens holds thousands of events, so no retrieval layer is needed.
- Add `tools=[{"type": "code_execution"}]` so Argon runs the statistics itself (30 s per run, pandas/numpy/matplotlib available, charts come back as inline images) and `response_format` for a fixed JSON: `{trend_summary, risk_tier, contributing_factors[], plain_language_explanation, questions_for_clinician[]}`. [code execution](https://ai.google.dev/gemini-api/docs/code-execution) · [structured output](https://ai.google.dev/gemini-api/docs/structured-output)
- Compute the risk tier in your own code (section 9) and have Argon *explain* it, not invent it. A model that free-styles a risk number is both less accurate and harder to defend.
- Feed the JSON back into the Live session with `send_client_content` so the voice agent can read the week back to the user.

### Audio files without a live session

One `gemini-3.8-flash` call accepts an audio file (WAV, MP3, M4A, Opus, WebM and more, up to 9.5 h, about 1,920 tokens per minute) plus a prompt and a JSON schema, and returns the structured record directly. Use this for carers who leave a voice memo rather than a conversation. [audio](https://ai.google.dev/gemini-api/docs/audio)

### Starting points and terms

- Fork `google-gemini/gemini-live-api-examples`, folder `gemini-live-ephemeral-tokens-websocket`: a vanilla-JS browser client with mic capture, PCM playback and function calling plus a `server.py` token backend; change the model string to `gemini-3.8-live`. The older `live-api-web-console` React app targets a shut-down model and needs porting. [repo](https://github.com/google-gemini/gemini-live-api-examples)
- Firebase AI Logic hides the API key for mobile apps but its Live support is still in preview and lists only `gemini-3.1-flash-live-preview`; for the hackathon a tiny token backend is faster. [Firebase AI Logic](https://firebase.google.com/docs/ai-logic/live-api?api=dev)
- Gemini API terms forbid use "in clinical practice, to provide medical advice" or in a way that needs medical-device clearance, and the unpaid tier uses prompts for training and may have them read by humans. Use the paid tier for anything real, synthetic data for the demo, and keep the app a diary aid rather than an advice engine. [terms](https://ai.google.dev/gemini-api/terms) · [use policy](https://policies.google.com/terms/generative-ai/use-policy)

### Architecture sketch

1. Web client (forked example): mic → 16 kHz PCM; plays 24 kHz PCM; shows both transcriptions live.
2. Token backend (FastAPI or Node): mints single-use Live tokens; stores events; serves the risk tier.
3. Live session on `gemini-3.8-live` with the diary system prompt and four flat tools.
4. Backend validates every tool call and writes rows; responds with `scheduling: WHEN_IDLE` so the model finishes its sentence.
5. After the session, `gemini-3.8-flash` turns the transcript into `DiaryEntry[]` JSON and reconciles with the tool rows.
6. Store as JSON/CSV now (SQLite or Firestore); wearable fields are just more columns.
7. Nightly and on-demand: `gemini-4-argon` with code execution over the CSV → trend JSON and charts; your code computes the tier; Argon explains it.
8. Narration: push the JSON into the next Live session so the agent can talk through it.

## Critique: where the idea is weak, and what to change

The concept is sound and the data is unusually good; the risks are over-promising on prediction, building a voice feature that is slower than a tap for the common case, and trying to ship the whole stack in a weekend. Ten points, hardest first.

1. **The risk score is the weakest part of the pitch and the most dangerous.** Day-ahead forecasting from diaries is close to infeasible (Chang 2025, and your own backtest: AUC 0.54 at 24 h). If a judge or a user hears "high risk" as "a seizure is coming", you either cause anxiety or get ignored after the first miss; only 40% of Seer's users found its forecast useful. Change: make the headline "risk now, next few hours" with reasons attached, and lead the pitch with logging, personal baseline and trigger discovery. Prediction is a supporting act.
2. **Voice-first is slower than a tap for the fourth seizure of the day.** The median event here lasts 33 seconds and 7% of days have three or more. A carer kneeling on the floor does not want a conversation. Change: a one-tap "just had one" that timestamps instantly (also a watch complication), with the Gemini conversation as the enrichment layer afterwards ("tell me about it when you're ready"). The conversation is the demo; the tap is what people still use in month three.
3. **Decide who the user is.** The data comes from a carer-managed, heavily medicalised case: parents give every dose, there is a VNS, past IVIG and a keto diet. Most adults with epilepsy self-manage and have far fewer seizures, and that market already has Epsy, Seer, SeizureTracker and the Epilepsy Foundation diary. The uncontested wedge is "for carers of people with frequent seizures": multi-carer logging (notes here mention a school nurse and a gymnastics coach), hand-over summaries, rescue-dose tracking. Say that on slide one.
4. **Trends can be artefacts of logging effort.** The 2026 rate rise coincides with more small events and more notes; overnight seizures are under-observed. Change: record logging effort (entries per day, check-ins completed, who logged) and show it beside every trend. The app should be able to say "you logged more small ones this month" instead of "your seizures went up".
5. **Your best signal has zero data behind it.** The pre-dose trough has one natural experiment behind it (the Sep 2025 re-timing) and no dose times; the diary has schedules only. Change: make dose logging nearly free (notification with a one-tap "taken", or an NFC sticker on the pill box) and show the dose-timing analysis as a roadmap item with a clearly labelled synthetic demo. Do not imply it has been tested.
6. **Do not let the watch imply prediction.** Heart rate is a reasonable detection signal for convulsive seizures and a decent source of bed and wake times; as a forecasting input it adds little on consumer sampling rates (section 6). Change: position the watch as "detects the big ones and tells us when you slept", not "predicts".
7. **Health data is leaving the device.** Voice recordings and a seizure diary are special-category data under UK GDPR; the Gemini free tier trains on prompts and may have humans read them, and the API terms forbid use that amounts to medical advice. Change: paid tier only, an explicit consent screen naming Google as a processor, redact names before upload, keep the score arithmetic in your own code (section 12 has the legal picture).
8. **The word "risk" may make it a medical device the day real users download it.** For the hackathon this does not matter; for the app store it does. Change: ship wording as "patterns from your own diary" and make the exportable clinic report, not the score, the product's output. See section 12.
9. **Scope.** Live voice plus extraction plus Argon analysis plus dashboard plus watch is a month of work. Build in this order and stop when time runs out: tap-and-voice logging with JSON extraction; the dashboard on the real diary; the risk-now replay; the clinic report. Put the watch on a slide.
10. **Tweaks worth adding, cheap and high value.**
    - A clinic report: a PDF of the last 90 days with counts by type, time-of-day histogram, convulsive and night-time counts, dose adherence, rescue doses, and the questions Argon drafted. The family already builds this by hand in Excel (the "Hourly analysis" tab); clinicians ask for exactly this.
    - A "change experiment": when a dose changes, auto-open a before-versus-after comparison with a confidence read-out. This family changed something roughly every two months for eight years and reversed at least one change on noise.
    - A seizure timer with live escalation at 5 and 10 minutes, on the watch too.
    - Trigger hypotheses as experiments the user can start: "You think hot showers set them off. Over 60 days: 8 showers logged, 3 followed by a seizure within 2 h, against 1 in 6 otherwise." Humble numbers, not verdicts.
    - An honest cold start: under 30 events, show only today's count and time since the last one, labelled "learning your pattern".

## Cross-check against the two research documents

Both documents agree with this brief on the big picture: time of day dominates, clustering is modest, no cycle is proven yet, and triggers must be logged every day to be testable. The trigger document corrected one real error here (the 2025 brivaracetam dates, now fixed above) and adds pharmacology this brief lacked; the gaps document's "trigger lab" framing is the sharper pitch and should become the demo centrepiece, with the risk level as the home screen.

### Where the trigger document differs or adds

| Topic | Trigger document | This brief | Verdict |
| --- | --- | --- | --- |
| 2025 brivaracetam dates | 1, 6 and 10 Sep 2025 (Excel day/month swap) | Originally 9 Jan, 9 Jun, 9 Oct | They are right; corrected. The step is real: seizures after 15:00 up 1.67-fold, mornings down |
| Day-to-day clustering | Weak and weakening: 74% vs 68% seizure-day chance in 2025 to 2026 | 45% to 73% by today's count, pooled over 8 years | Both right. The effect has shrunk as the base rate rose (78% of days now have a seizure). Weight "yesterday" per person and per era; today's count and the 7-day count carry more |
| Day-ahead forecast | Logistic AUC 0.63 (any), 0.59 (severe) | Hourly model AUC 0.54 at 24 h, 0.76 at 3 h, 0.78 severe at 6 h | Consistent: day-level is weak, hour-level is the product |
| Missed doses | 8 notes, including a vomited evening dose on 9 Jul 2020 followed by 3 seizures by 08:00, and cenobamate 4 h late on 1 Aug 2023 | 2 notes (narrower search) | Theirs is better: count vomiting as a lost dose and log it |
| Menstrual cycle | 8 usable cycles; perimenstrual phase has the *lowest* rate (1.20 a day) | 11 flags, no effect | Agree. The 63% severe share among "period" notes is probably note-selection bias. Keep logging |
| Period flags begin Aug 2025 | Read as a change in logging routine | Missed | Adopt: track logging effort and show it beside trends |
| Severe seizures since Sep 2025 | 7.5 to 8.8 per 30 days | Same | Agree: the rise is in small seizures |

### What the trigger document adds that this brief lacked

- Drug interactions worth an in-app note when a medicine is added (informational, never advice): cenobamate inhibits CYP2C19 and raised brivaracetam levels about 27% in 16 of 19 patients, with fatigue that eased when brivaracetam was cut; it raises clobazam's active metabolite, lowers lamotrigine 21 to 52% and carbamazepine 23%, and can weaken hormonal contraception. [Bender 2025](https://www.frontiersin.org/journals/pharmacology/articles/10.3389/fphar.2025.1571376/full)
- Half-lives in context: cenobamate 30 to 76 h (dose timing matters little), brivaracetam about 9 h (timing matters a lot). The dose-timing feature should concentrate on short-half-life drugs.
- Chronotherapy: small studies report better control when the larger share of a dose is given before the person's usual seizure time. Her 15:00 to 22:00 peak argues for afternoon cover. Evidence for the neurologist, not an app recommendation. [chronotherapy review](https://pmc.ncbi.nlm.nih.gov/articles/PMC5751908)
- VNS magnet use: 21 notes in 2021 describe swipes with mixed results. Log magnet use and outcome.
- Side effects drove every dose change since 2023 (exhaustion, double vision). A daily fatigue and side-effect rating is a first-class field, not an extra.
- Drug-resistant epilepsy framing: after two failed drugs, gains are partial (each failed regimen raises the odds of the next failing, OR 1.73), so measure rate and severity changes, not seizure freedom. [Chen 2018](https://pmc.ncbi.nlm.nih.gov/articles/PMC5885858)
- "Big event tomorrow" as a check-in field, and backfilling external data (weather, daylight, term dates) for every day so it has a denominator.

### What the gaps and competitor document adds

- The framing. "Suggest any trigger; the agent finds or creates the data, runs the test, and reports Confirmed, Not enough evidence yet, or Rejected as misleading" is a better headline than "diary plus risk", and it is exactly where Argon earns its place: Argon proposes and runs the analysis, deterministic code owns the numbers people act on. Keep the risk level as the home screen; make the trigger lab the demo centrepiece.
- Statistical hygiene shown on screen: permutation tests, holdout backtests, confounder checks (the naive "clobazam makes things worse" is confounding by indication, as the rescue-dose analysis in section 3 shows), Benjamini–Hochberg correction across many tested triggers, and rejected findings displayed rather than hidden.
- N-of-1 framing for medication changes: only five single-patient trials exist in epilepsy, so the before-and-after report is evidence for the neurologist and never a recommendation. [Defelippe 2024](https://researchinformation.umcutrecht.nl/en/publications/n-of-1-trials-in-epilepsy-a-systematic-review-and-lessons-paving-/)
- About half of seizures are never logged and 86% of sleep seizures are missed, so overnight hours should read "no data", not "low". [Hoppe 2007](https://www.sciencedaily.com/releases/2007/11/071112163616.htm)
- Competitors: Nile claims trigger insights with no statistical testing; Seer's cycle forecast is the prior art for time-of-day risk and should be cited, not claimed. Use "we could not find a tool that does this".
- Their backtest figure (12.1% of seizure-hours in HIGH vs 0.8% in LOW) and this brief's (25% vs 3.4% chance within 3 h) use different definitions. Agree on one before it goes on a slide.

### Gaps neither document covers, worth a look

- Non-epileptic events. The diary has NES rows, and in Sep 2019 a carbamazepine increase was reversed because the rise turned out to be non-epileptic; in one video-EEG cohort 58% of reported events were not epileptic. Add a "possibly non-epileptic" tag and separate them in the clinic report.
- Validated instruments clinicians recognise: the Liverpool Adverse Events Profile for side effects, NDDI-E for depression, a seizure-severity questionnaire. Cheap to implement, and they make the report legible to a neurologist (section on clinic reports, below).
- Video. SeizureTracker's one-tap timer-plus-video is the feature neurologists value most for classifying seizure type. A ten-second clip button beside "just had one".
- Multi-carer roles (parent, sibling, school nurse, coach) with hand-over summaries and per-role visibility; privacy across several carers is a documented diary problem.
- Emergency plan in the format schools and ambulances expect (individual healthcare plan, buccal midazolam protocol), so the care-plan screen can be printed and handed over.
- Patient autonomy. She is an adult at drama school: patient-logged entries, the evening "do you feel one coming?" prompt, and consent over who sees what.
- Other medical events as a record type: the July 2026 sleep study, the 11 May 2026 admission, IVIG and rituximab courses. They belong on the timeline next to medication changes.

## Is the risk score legal? Caveats, safety and ethics

A voice diary with trend charts is not a medical device. A per-person "seizure risk: high / medium / low" computed from that diary almost certainly is one in the UK, EU and US the moment the public can download it. For the hackathon demo that changes nothing; for an app-store release it changes everything. This is a reading of the official guidance, not legal advice.

### Where the line is

| Feature | UK (MHRA, UK MDR 2002) | EU (MDR 2017/745) | US (FDA) |
| --- | --- | --- | --- |
| Voice diary, reminders, trend and cycle charts, clinic report | Not a device: replaces a written symptom diary; "general-purpose recording" | Wellness and diary apps excluded (MDCG 2019-11 rev.1) | Not device CDS if it only displays the person's own records |
| Per-person risk level from their own entries | "Likely a device": MHRA names "Predicts", "Risk of", "Calculates" as device-indicative; a disclaimer or "research use only" label does not undo it | Device; Rule 11 puts software informing diagnostic or therapeutic decisions in Class IIa at least, needing a notified body | Device: patient- or carer-facing software fails Cures Act criterion 3; FDA's own examples include predicting events "in the next 24 hours" |
| Adding smartwatch heart rate to that risk | Same, plus "monitoring linked to a specific disease" | Rule 11 monitoring clause; heart rate can push to IIb | Analysing a continuous physiological pattern fails criterion 1 |

Sources: [MHRA stand-alone software guidance](https://assets.publishing.service.gov.uk/media/6abf6c8c943e890cb55e5e52/Medical_device_stand-alone_software_including_apps__including_IVDMDs.pdf) · [MDR text](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32017R0745) · [MDCG 2019-11 rev.1](https://health.ec.europa.eu/document/download/b45335c5-1679-4c71-a91c-fc7a4d37f12b_en) · [FDA CDS guidance, Jan 2026](https://www.fda.gov/media/109618/download) · [FDA general wellness policy](https://www.fda.gov/media/90652/download)

### What triggers the obligations

- "Placing on the market" means making it available, paid or free, by any route including app stores. A judged demo on your own devices with your own or synthetic data is not placing on the market. The manufacturer is whoever puts their name on it, so three students can be a manufacturer.
- Today most standalone software in Great Britain is Class I (self-declaration plus MHRA registration), with post-market surveillance rules in force since 16 June 2025. The pre-market reform is expected to be adopted around December 2026 and in force June 2027, with IMDRF-style classification that practitioners expect to put most software like this in Class IIa. If you go on past the hackathon, plan for IIa, not I. [UK reform timeline](https://www.hlc.com/en/publications/uk-medical-devices-reform-mhra-publishes) · [MHRA implementation page](https://gov.uk/government/publications/implementation-of-the-future-regulation-of-medical-devices/implementation-of-the-future-regulations)
- Testing the risk feature on real patients to see whether it works is a clinical investigation: ethics review and notification to MHRA 60 days ahead. [MHRA clinical investigations](https://www.gov.uk/guidance/notify-mhra-about-a-clinical-investigation-for-a-medical-device)
- The MHRA AI Airlock (phase 3 opened 6 Oct 2026) takes prototypes ready to be trialled; it de-risks a product, it is not a route to market and not for a weekend build. [AI Airlock](https://www.gov.uk/government/publications/ai-airlock-phase-3-application)
- Comparators: Empatica's EpiMonitor and EpiWatch are cleared for *detection* of convulsive seizures, not forecasting. Seer released its risk forecast in Australia as a wellness product in 2022; Australia's software exclusions expressly do not exclude prediction or prognosis of a serious disease, and Seer entered administration in early 2025. Nobody has a cleared seizure-forecasting product. [Empatica](https://empatica.com/en-gb/epimonitor) · [Australian exclusions](https://legislation.gov.au/F2021L00047/asmade/2021-01-15/text/original/epub/OEBPS/document_1/document_1.html)

### App stores

- Apple 1.4.1: medical apps get closer review; health-measurement claims need disclosed data and methodology; remind users to consult a doctor; healthcare apps should be submitted by a legal entity; health data may never be used for ads. [Apple guidelines](https://developer.apple.com/app-store/review/guidelines/)
- Google Play: complete the health-apps declaration; a non-device health app must state in its description that it is not a medical device and does not diagnose, treat, cure or prevent; all health apps must remind users to consult a professional. [Google Play health policy](https://support.google.com/googleplay/android-developer/answer/12261419)

### Data protection and Gemini

- A seizure diary is special-category health data under UK GDPR, and so is an inferred risk level. You need an Article 6 basis and an Article 9 condition; for a consumer app that is explicit, separate, unticked, withdrawable consent. Do a DPIA: wearables and AI count as innovative technology and a breach could endanger physical safety. [ICO special category data](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/special-category-data/what-is-special-category-data/) · [ICO DPIA](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/data-protection-impact-assessments-dpias/when-do-we-need-to-do-a-dpia/)
- Gemini API terms (23 Mar 2026): on the unpaid tier Google uses content to improve products and humans may read it, and you must not submit sensitive personal data; the paid tier does not train on prompts and falls under the Data Processing Addendum (UK and EEA users get paid-tier data terms even on free quota). The use restrictions bar clinical practice, medical advice, and anything that needs clearance from a device regulator. For UK data residency use the enterprise platform in `europe-west2`. [Gemini terms](https://ai.google.dev/terms) · [UK residency](https://blog.google/around-the-globe/google-europe/united-kingdom/data-residency-machine-learning-processing-uk)
- Tell users in one screen: recordings and entries go to Google's Gemini API, which tier, where processed, how long kept, how to withdraw.
- NHS adoption later would need DTAC: a DCB0129 clinical safety case with a named Clinical Safety Officer, MHRA status statement, DPIA, DSPT, Cyber Essentials and penetration testing. [DTAC](https://transform.england.nhs.uk/key-tools-and-info/digital-technology-assessment-criteria-dtac/)

### Wording that keeps you on the right side

- Avoid: "predicts your next seizure", "seizure risk", "safe to drive", "you can skip your dose", "detects seizures", and any accuracy figure you have not validated.
- Prefer: "pattern insights from your own diary", "your diary shows more seizures in the evenings", "weeks like this one have had more seizures in your log", shown as history and cycle charts rather than a traffic light. For the demo, label the tier screen "research prototype" on the slide and in the UI.
- Driving: never imply fitness to drive; UK law requires stopping after any seizure and telling the DVLA. [gov.uk](https://www.gov.uk/epilepsy-and-driving)
- Emergency card, always one tap away: call 999 (112) if a seizure lasts over 5 minutes or longer than usual, repeats without recovery, is the first ever, causes injury or breathing is difficult; note start and end time; nothing in the mouth; recovery position afterwards. [NHS](https://www.nhs.uk/conditions/what-to-do-if-someone-has-a-seizure-fit/)
- Draft disclaimer for the store listing and first run: "This app is a diary and pattern-review tool for people with diagnosed epilepsy. It is not a medical device, does not predict or detect seizures, and does not diagnose, treat or prevent any condition. Insights come from your own entries and may be wrong; never change medication, drive, or make safety decisions based on them. Discuss patterns with your clinician, and call 999 in an emergency."

### Bottom line

- Fine for the hackathon: everything in this doc, on your own devices, with the diary anonymised or with synthetic data, and the risk screen labelled a research prototype.
- The day real users can download it, you are a manufacturer: MHRA registration, UKCA or CE conformity, clinical evidence, post-market surveillance, app-store medical rules, and Gemini's terms all apply to the risk feature specifically. The diary, charts and clinic report carry none of that.
- The three cheapest risk reducers: reword the feature as pattern insights for discussion with a clinician and show history rather than a forecast; use the paid Gemini tier with a one-screen privacy notice and separate consent; hard-code the 5-minute/999 card and the disclaimer, and write a one-page DPIA before any human outside the team tries it.

## Sources

Every looked-up fact is linked where it appears. The ones worth reading in full, by topic:

- Your data: `seizure diary xlsx (data/raw/seizure_duration_analysis.xlsx)` (Seizure Data tab) and `medication chart xlsx (data/raw/medication_chart.xlsx)` (Meds Changes, Current, weekly tabs); analysis scripts and results are in the pack sent alongside this doc.
- Cycles: [Baud 2018, Nature Communications](https://pmc.ncbi.nlm.nih.gov/articles/PMC5758806) · [Leguia 2021, JAMA Neurology](https://jamanetwork.com/journals/jamaneurology/article-abstract/2775979) · [Karoly 2018 diary cycles (summary)](https://www.neurologylive.com/view/epileptic-seizure-cycles-found-patient-specific-robust) · [Karoly 2021, six misconceptions](https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2021.720328/full)
- Forecasting from diaries: [Karoly 2020](https://www.medrxiv.org/content/10.1101/2019.12.19.19015453.full.pdf) · [Seer prospective validation](https://aesnet.org/abstractslisting/prospective-validation-of-a-mobile-and-wearable-app-to-forecast-seizure-risk) · [Goldenholz prospective](https://www.medrxiv.org/content/10.1101/2024.01.11.24301175v1.full.pdf) · [Chang 2025](https://research.bidmc.org/daniel-goldenholz/publications/rigorous-evaluation-five-models-e-diary-only-seizure-forecasting-retrospective-and) · [Stirling 2021 wearables](https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2021.704060/full)
- Triggers and self-prediction: [Haut 2007](https://www.aan.com/PressRoom/home/PressRelease/433) · [Haut 2012 e-diary](https://pubmed.ncbi.nlm.nih.gov/22424857) · [Nakken 2005](https://pubmed.ncbi.nlm.nih.gov/15652738/) · [stress diary study](https://aesnet.org/abstractslisting/stress-is-associated-with-an-increased-risk-of-seizures-in-persons-with-epilepsy--results-of-a-diary-study) · [sleep timing, Brain 2023](https://seermedical.com/research/sleep-and-seizure-risk-in-epilepsy-bed-and-wake-times-are-more-important-than-sleep-duration) · [Rakers 2017 weather](https://idw-online.de/de/news675088) · [UCL heatwaves](https://www.ucl.ac.uk/news/2024/sep/heatwaves-may-increase-likelihood-seizures-people-epilepsy)
- Clinical thresholds and safety: [ILAE status epilepticus timings](https://link.springer.com/10.1186/s12883-022-02868-y) · [clusters, Haut 2022](https://www.lgsfoundation.org/wp-content/uploads/2021/08/Epilepsia-2022-Haut-Recognizing-seizure-clusters-in-the-community-The-path-to-uniformity-and-individualization-in-1.pdf) · [AAN SUDEP guideline](https://www.aan.com/Guidelines/home/GetGuidelineContent/852) · [Swedish SUDEP study](https://www.cureepilepsy.org/news/clinical-risk-factors-in-sudep-a-nationwide-population-based-case-control-study/) · [ILAE drug monitoring guideline (half-lives)](https://discovery-pp.ucl.ac.uk/id/eprint/10049571/1/Patsalos%20Patsalos%20et%20al%202018-AED%20%20TDM-Manuscript-Revision%201-24_05_18-FINAL.pdf)
- Wearables: [ILAE/IFCN wearable detection guideline](https://ilae.org/files/ilaeGuideline/Automjated-seizure-detection-using-wearable-devices---epi.16818.pdf) · [HRV scoping review](https://www.mdpi.com/2077-0383/13/3/747) · [Apple heart-rate white paper](https://apple.com.cn/health/pdf/Heart_Rate_Calorimetry_Activity_on_Apple_Watch_November_2024.pdf) · [EpiWatch 510(k)](https://fda.innolitics.com/device/K243515) · [EpiMonitor 510(k)](https://fda.innolitics.com/device/K250515) · [NightWatch 510(k)](https://fda.innolitics.com/device/K243199)
- Gemini: [models](https://ai.google.dev/gemini-api/docs/models) · [Gemini 4 Argon](https://ai.google.dev/gemini-api/docs/models/gemini-4-argon) · [3.8 Live](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-live) · [Live API capabilities](https://ai.google.dev/gemini-api/docs/live-api/capabilities) · [Live tools](https://ai.google.dev/gemini-api/docs/live-api/tools) · [structured output](https://ai.google.dev/gemini-api/docs/structured-output) · [code execution](https://ai.google.dev/gemini-api/docs/code-execution) · [API terms](https://ai.google.dev/gemini-api/terms) · [example repo](https://github.com/google-gemini/gemini-live-api-examples)
