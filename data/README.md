# data/

Everything in this folder except this README is gitignored: it is one real person's health record. Share it out-of-band, never through git, and never send names or the NHS number to Gemini (redact first).

| File | What it is |
| --- | --- |
| `seizures_clean.csv` | 2,598 seizures, Jan 2018 – Aug 2026. Columns: `date, start_time, hour, duration_s, type, severity_HL, unsure, clobazam_rescue_10mg, period_day1, notes`. **`notes` still contains the patient's first name**, so redact it before it goes anywhere external. |
| `medication_timeline.csv` | 47 medication events: `date, drug, action, detail` |
| `samsung_daily_features.csv` | ~200 days of watch-derived features (resting/night/day HR, HRV, sleep timing/duration/score, stress, steps) joined with `sz_today`, `sz_tomorrow` |
| `daily_feature_correlations.csv` | Spearman correlations of those features vs seizures (`feature, target, n, rho, p, low/high tercile means`) |
| `raw/seizure_duration_analysis.xlsx` | Source diary spreadsheet ("Shaan Copy of Seizure Duration Analysis"); main sheet `Seizure Data` plus Weekly / Totals / Pivot / Hourly sheets |
| `raw/medication_chart.xlsx` | Source medication chart: `Meds Changes`, `Meds Levels`, `Current`, `Holiday`, then one sheet per week 2018 – 2021. **Header rows carry the patient's name and NHS number.** |
| `raw/samsung_health_export.zip` | Full Samsung Health export (47 MB, not unpacked) |
| `raw/samsung_hr_minutes.csv` | Per-minute heart rate from the export (5 MB) |
