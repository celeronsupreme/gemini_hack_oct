import pandas as pd, numpy as np, json, glob, csv, os, sys
from scipy import stats
ROOT = sys.argv[1]
OUT = {}
TZ = 'Europe/London'
def load(name):
    f = f'{ROOT}/{name}.20261031121818.csv'
    with open(f, encoding='utf-8-sig') as fh:
        fh.readline(); hdr = next(csv.reader([fh.readline()]))
    df = pd.read_csv(f, skiprows=2, header=None, names=hdr+['_x'], index_col=False, low_memory=False, encoding='utf-8-sig')
    df.columns = [c.split('.')[-1] if c.startswith('com.samsung') else c for c in df.columns]
    return df
ev = pd.read_pickle('events.pkl')
evt = ev[ev['ts'].notna()].copy()
evt['ts_local'] = evt['ts'].dt.tz_localize(TZ, ambiguous='NaT', nonexistent='shift_forward')

# ---------- per-minute heart rate ----------
hr = load('com.samsung.shealth.tracker.heart_rate')
rows = []
for _, r in hr[hr['binning_data'].notna()].iterrows():
    fn = r['binning_data']
    paths = glob.glob(f'{ROOT}/jsons/com.samsung.shealth.tracker.heart_rate/*/{fn}')
    if not paths: continue
    try:
        for b in json.load(open(paths[0])):
            rows.append((b['start_time'], b.get('heart_rate'), b.get('heart_rate_min'), b.get('heart_rate_max')))
    except Exception: pass
hrm = pd.DataFrame(rows, columns=['ms', 'hr', 'hr_min', 'hr_max']).dropna(subset=['hr'])
hrm['t'] = pd.to_datetime(hrm['ms'], unit='ms', utc=True).dt.tz_convert(TZ)
# spot measurements (single readings) as extra minutes
spot = hr[hr['binning_data'].isna() & (hr['heart_beat_count'] <= 1)].copy()
spot_t = pd.to_datetime(spot['start_time'])  # local wall time per time_offset; treat as local
spot_t = spot_t.dt.tz_localize(TZ, ambiguous='NaT', nonexistent='shift_forward')
spot_df = pd.DataFrame({'t': spot_t, 'hr': spot['heart_rate'].astype(float), 'hr_min': spot['min'], 'hr_max': spot['max']}).dropna(subset=['t'])
hrm = pd.concat([hrm[['t', 'hr', 'hr_min', 'hr_max']], spot_df]).sort_values('t')
hrm['t'] = hrm['t'].dt.tz_convert('UTC').dt.floor('min').dt.tz_convert(TZ)
hrm = hrm.groupby('t').agg(hr=('hr', 'mean'), hr_min=('hr_min', 'min'), hr_max=('hr_max', 'max')).reset_index()
OUT['hr_minutes'] = int(len(hrm)); OUT['hr_range'] = [str(hrm['t'].min()), str(hrm['t'].max())]
hrm['date'] = hrm['t'].dt.tz_localize(None).dt.normalize()
cov = hrm.groupby('date').size()
win = (hrm['t'] >= '2025-08-18') & (hrm['t'] < '2026-03-05')
OUT['hr_minutes_in_watch_window'] = int(win.sum())
days_in_window = pd.date_range('2025-08-18', '2026-03-04', freq='D')
cov_w = cov.reindex(days_in_window, fill_value=0)
OUT['days_with_hr'] = int((cov_w > 0).sum()); OUT['days_in_window'] = len(days_in_window)
OUT['median_hr_minutes_per_covered_day'] = float(cov_w[cov_w > 0].median())
OUT['hr_coverage_by_hour_pct'] = (hrm[win].groupby(hrm[win]['t'].dt.hour).size() / (OUT['days_with_hr'] * 60) * 100).round(1).reindex(range(24), fill_value=0).tolist()
hrm.to_pickle('hr_minutes.pkl')

# ---------- peri-ictal heart rate ----------
hr_idx = hrm.set_index('t')['hr']
hr_max_idx = hrm.set_index('t')['hr_max']
def seg(center, a, b, series=hr_idx):
    s = series[(series.index >= center + pd.Timedelta(minutes=a)) & (series.index < center + pd.Timedelta(minutes=b))]
    return s
peri = []
for _, r in evt[(evt['ts_local'] >= '2025-08-18') & (evt['ts_local'] < '2026-03-05')].iterrows():
    c = r['ts_local']
    if pd.isna(c): continue
    base = seg(c, -40, -10); pre = seg(c, -10, 0); ict = seg(c, 0, 5); ictmax = seg(c, -2, 5, hr_max_idx); post = seg(c, 5, 20)
    if len(base) >= 10 and len(ict) >= 2:
        peri.append(dict(ts=c, sev=r['sev'], typ=r['type'], dur=r['dur_s'], base=base.median(), pre=pre.median() if len(pre) else np.nan, ict=ict.mean(), ictmax=ictmax.max(), post=post.median() if len(post) else np.nan))
peri = pd.DataFrame(peri)
OUT['n_seizures_in_watch_window'] = int(((evt['ts_local'] >= '2025-08-18') & (evt['ts_local'] < '2026-03-05')).sum())
OUT['n_seizures_with_hr_coverage'] = int(len(peri))
if len(peri):
    peri['delta'] = peri['ict'] - peri['base']; peri['delta_max'] = peri['ictmax'] - peri['base']
    for lab, sub in [('all', peri), ('H', peri[peri['sev'] == 'H']), ('L', peri[peri['sev'] == 'L'])]:
        OUT[f'peri_{lab}'] = dict(n=int(len(sub)), base_median=float(sub['base'].median()), ict_mean_median=float(sub['ict'].median()), delta_median=float(sub['delta'].median()), delta_max_median=float(sub['delta_max'].median()), pct_delta_max_ge20=float((sub['delta_max'] >= 20).mean() * 100), pct_delta_max_ge30=float((sub['delta_max'] >= 30).mean() * 100), pct_rise_ge10=float((sub['delta'] >= 10).mean() * 100))
    # control: random non-seizure minutes matched by hour of day, same window
    rng = np.random.default_rng(1)
    ctrl = []
    cand = hrm[win & (hrm['t'].dt.hour.between(10, 23))].copy()
    sz_times = evt['ts_local'].dropna()
    tries = 0
    while len(ctrl) < 400 and tries < 5000:
        tries += 1
        c = cand.iloc[rng.integers(len(cand))]['t']
        # exclude if any seizure within +-60 min
        if ((sz_times - c).abs() < pd.Timedelta(minutes=60)).any(): continue
        base = seg(c, -40, -10); ict = seg(c, 0, 5); ictmax = seg(c, -2, 5, hr_max_idx)
        if len(base) >= 10 and len(ict) >= 2:
            ctrl.append(dict(base=base.median(), ict=ict.mean(), ictmax=ictmax.max()))
    ctrl = pd.DataFrame(ctrl); ctrl['delta'] = ctrl['ict'] - ctrl['base']; ctrl['delta_max'] = ctrl['ictmax'] - ctrl['base']
    OUT['peri_control'] = dict(n=int(len(ctrl)), delta_median=float(ctrl['delta'].median()), delta_max_median=float(ctrl['delta_max'].median()), pct_delta_max_ge20=float((ctrl['delta_max'] >= 20).mean() * 100), pct_delta_max_ge30=float((ctrl['delta_max'] >= 30).mean() * 100), pct_rise_ge10=float((ctrl['delta'] >= 10).mean() * 100))
    OUT['peri_mannwhitney_p_all_vs_ctrl'] = float(stats.mannwhitneyu(peri['delta_max'], ctrl['delta_max']).pvalue)
    OUT['peri_mannwhitney_p_H_vs_ctrl'] = float(stats.mannwhitneyu(peri[peri['sev'] == 'H']['delta_max'], ctrl['delta_max']).pvalue) if (peri['sev'] == 'H').sum() > 5 else None
    # pre-ictal: 10 min before vs baseline
    OUT['pre_minus_base_median_all'] = float((peri['pre'] - peri['base']).median())
    peri.to_pickle('peri.pkl')

# ---------- daily features ----------
d = {}
hw = hrm[win].copy(); hw['hour'] = hw['t'].dt.hour
d['resting_hr'] = hw.groupby('date')['hr'].quantile(0.05)
d['night_hr'] = hw[hw['hour'].between(2, 5)].groupby('date')['hr'].mean()
d['day_hr'] = hw[hw['hour'].between(10, 20)].groupby('date')['hr'].mean()
d['hr_minutes'] = hw.groupby('date').size()
# stress
st = load('com.samsung.shealth.stress'); st['t'] = pd.to_datetime(st['start_time']); st = st[st['t'] >= '2025-08-18']
st['date'] = st['t'].dt.normalize(); d['stress_mean'] = st.groupby('date')['score'].mean(); d['stress_max'] = st.groupby('date')['score'].max()
# hrv (hourly rows with json of 30-s samples): use row-level by reading json means
hv = load('com.samsung.health.hrv'); hvrows = []
for _, r in hv.iterrows():
    paths = glob.glob(f'{ROOT}/jsons/com.samsung.health.hrv/*/{r["binning_data"]}')
    if not paths: continue
    try:
        js = json.load(open(paths[0]))
        for b in js: hvrows.append((b['start_time'], b.get('rmssd'), b.get('sdnn')))
    except Exception: pass
hvd = pd.DataFrame(hvrows, columns=['ms', 'rmssd', 'sdnn']); hvd['t'] = pd.to_datetime(hvd['ms'], unit='ms', utc=True).dt.tz_convert(TZ); hvd['date'] = hvd['t'].dt.tz_localize(None).dt.normalize(); hvd['hour'] = hvd['t'].dt.hour
d['hrv_rmssd_night'] = hvd[hvd['hour'].between(1, 6)].groupby('date')['rmssd'].mean(); d['hrv_rmssd_day'] = hvd[~hvd['hour'].between(1, 6)].groupby('date')['rmssd'].mean()
OUT['hrv_samples'] = int(len(hvd))
# skin temperature (nightly)
skt = load('com.samsung.health.skin_temperature'); skt['t'] = pd.to_datetime(skt['start_time']); skt['date'] = skt['t'].dt.normalize()
d['skin_temp'] = skt.groupby('date')['temperature'].mean()
# sleep
sl = load('com.samsung.shealth.sleep'); sl = sl[sl['has_sleep_data'] == 1].copy()
sl['start'] = pd.to_datetime(sl['start_time']); sl['end'] = pd.to_datetime(sl['end_time'])
sl = sl[(sl['end'] - sl['start']) > pd.Timedelta(hours=2)]
sl['date'] = sl['end'].dt.normalize()  # the morning it ended
sl['dur_h'] = (sl['end'] - sl['start']).dt.total_seconds() / 3600
sl['bed_h'] = ((sl['start'].dt.hour + sl['start'].dt.minute / 60 + 12) % 24) - 12  # hours relative to midnight (negative = before midnight)
sl['wake_h'] = sl['end'].dt.hour + sl['end'].dt.minute / 60
slg = sl.groupby('date').agg(dur_h=('dur_h', 'sum'), bed_h=('bed_h', 'first'), wake_h=('wake_h', 'last'), sleep_score=('sleep_score', 'first'), efficiency=('efficiency', 'first'))
for c in slg.columns: d['sleep_' + c] = slg[c]
OUT['sleep_nights'] = int(len(slg)); OUT['sleep_nights_in_window'] = int(((slg.index >= '2025-08-18') & (slg.index < '2026-03-05')).sum())
# steps
pdm = load('com.samsung.shealth.tracker.pedometer_day_summary'); pdm['date'] = pd.to_datetime(pdm['day_time']).dt.normalize()
d['steps'] = pdm.groupby('date')['step_count'].max()
feat = pd.DataFrame(d)
feat['sleep_bed_shift'] = (feat['sleep_bed_h'] - feat['sleep_bed_h'].rolling(7, min_periods=3).median().shift(1)).abs()
feat['sleep_wake_shift'] = (feat['sleep_wake_h'] - feat['sleep_wake_h'].rolling(7, min_periods=3).median().shift(1)).abs()
# seizure counts
days = pd.date_range(ev['date'].min(), ev['date'].max(), freq='D')
daily = ev.groupby('date').size().reindex(days, fill_value=0); dailyH = ev[ev['sev'] == 'H'].groupby('date').size().reindex(days, fill_value=0)
feat['sz_today'] = daily.reindex(feat.index); feat['sz_tomorrow'] = daily.shift(-1).reindex(feat.index); feat['H_today'] = dailyH.reindex(feat.index)
featw = feat[(feat.index >= '2025-08-18') & (feat.index <= '2026-03-04')].copy()
featw.to_pickle('daily_features.pkl')
res = []
for c in ['resting_hr', 'night_hr', 'day_hr', 'stress_mean', 'stress_max', 'hrv_rmssd_night', 'hrv_rmssd_day', 'skin_temp', 'sleep_dur_h', 'sleep_bed_h', 'sleep_wake_h', 'sleep_sleep_score', 'sleep_efficiency', 'sleep_bed_shift', 'sleep_wake_shift', 'steps']:
    for target in ['sz_today', 'sz_tomorrow', 'H_today']:
        sub = featw[[c, target]].dropna()
        if len(sub) < 20: continue
        rho, p = stats.spearmanr(sub[c], sub[target])
        q = sub[c].quantile([1/3, 2/3])
        lo = sub[sub[c] <= q.iloc[0]][target].mean(); hi = sub[sub[c] >= q.iloc[1]][target].mean()
        res.append(dict(feature=c, target=target, n=len(sub), rho=round(float(rho), 3), p=round(float(p), 4), low_tercile_mean=round(float(lo), 2), high_tercile_mean=round(float(hi), 2)))
res = pd.DataFrame(res); res.to_csv('daily_feature_correlations.csv', index=False)
OUT['daily_feature_correlations'] = res.to_dict('records')
# same-day HR vs seizures: within-day means (day_hr) on seizure days vs not, restricted to watch days
OUT['feature_days_with_hr'] = int(featw['resting_hr'].notna().sum())

# ---------- menstrual cycle from flow log ----------
fl = load('com.samsung.health.cycle.flow'); fl['t'] = pd.to_datetime(fl['start_time']).dt.normalize().sort_values()
flow_days = sorted(fl['t'].unique())
starts = [flow_days[0]] + [d2 for d1, d2 in zip(flow_days[:-1], flow_days[1:]) if (d2 - d1).days >= 10]
starts = [s for s in starts if s <= ev['date'].max()]
OUT['flow_days'] = len(flow_days); OUT['cycle_starts'] = [str(s.date()) for s in starts]
# phases: perimenstrual -3..+3 (excluding none), follicular 4..11, ovulatory 12..16, luteal 17..cycle end-4
rates = {'perimenstrual': [], 'follicular': [], 'ovulatory': [], 'luteal': []}
cyc = []
for s1, s2 in zip(starts[:-1], starts[1:]):
    L = (s2 - s1).days
    if L < 20 or L > 45: continue
    cyc.append(L)
    for off in range(-3, L - 3):
        dd = s1 + pd.Timedelta(days=off)
        if dd not in daily.index: continue
        if -3 <= off <= 3: ph = 'perimenstrual'
        elif 4 <= off <= 11: ph = 'follicular'
        elif 12 <= off <= 16: ph = 'ovulatory'
        else: ph = 'luteal'
        rates[ph].append(daily[dd])
OUT['usable_cycles'] = len(cyc); OUT['cycle_lengths'] = cyc
OUT['phase_rates'] = {k: dict(days=len(v), per_day=round(float(np.mean(v)), 2) if v else None) for k, v in rates.items()}
if rates['perimenstrual'] and rates['luteal']:
    OUT['phase_kruskal_p'] = float(stats.kruskal(*[v for v in rates.values() if v]).pvalue)
# severe seizures by phase
ratesH = {k: [] for k in rates}
for s1, s2 in zip(starts[:-1], starts[1:]):
    L = (s2 - s1).days
    if L < 20 or L > 45: continue
    for off in range(-3, L - 3):
        dd = s1 + pd.Timedelta(days=off)
        if dd not in dailyH.index: continue
        ph = 'perimenstrual' if -3 <= off <= 3 else 'follicular' if 4 <= off <= 11 else 'ovulatory' if 12 <= off <= 16 else 'luteal'
        ratesH[ph].append(dailyH[dd])
OUT['phase_rates_H'] = {k: round(float(np.mean(v)), 3) if v else None for k, v in ratesH.items()}

# ---------- exercise ----------
ex = load('com.samsung.shealth.exercise'); ex['start'] = pd.to_datetime(ex['start_time']); ex['end'] = pd.to_datetime(ex['end_time']); ex = ex[ex['start'] >= '2019-01-01']
ex['dur_min'] = (ex['end'] - ex['start']).dt.total_seconds() / 60
ex = ex[ex['dur_min'] >= 10]
OUT['exercise_sessions'] = int(len(ex)); OUT['exercise_types'] = ex['exercise_type'].value_counts().head(6).to_dict()
sz = evt['ts'].dropna()
after = 0; during = 0
for _, r in ex.iterrows():
    after += ((sz > r['end']) & (sz <= r['end'] + pd.Timedelta(hours=2))).sum()
    during += ((sz >= r['start']) & (sz <= r['end'])).sum()
exp_hours = len(ex) * 2
# baseline seizures per hour in the same clock hours on days without exercise
hrs = ex['end'].dt.hour
base_rate = evt[evt['hour'].isin(hrs.unique())].groupby('date').size().reindex(days, fill_value=0)
nonex_days = days.difference(pd.DatetimeIndex(ex['start'].dt.normalize().unique()))
per_hour_base = base_rate.reindex(nonex_days).mean() / len(hrs.unique())
OUT['exercise_after2h_seizures'] = int(after); OUT['exercise_during_seizures'] = int(during); OUT['exercise_after2h_rate_per_h'] = round(after / exp_hours, 3); OUT['exercise_baseline_rate_per_h_matched_hours'] = round(float(per_hour_base), 3)
json.dump(OUT, open('samsung_results.json', 'w'), indent=1, default=str)
print(json.dumps({k: v for k, v in OUT.items() if k not in ('daily_feature_correlations', 'hr_coverage_by_hour_pct')}, indent=1, default=str))
print(res.sort_values('p').head(20).to_string())
