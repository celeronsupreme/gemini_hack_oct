import pandas as pd, numpy as np, json
from scipy import stats, signal
ev = pd.read_pickle('events.pkl')
out = {}

# ---------- daily series ----------
days = pd.date_range(ev['date'].min(), ev['date'].max(), freq='D')
daily = ev.groupby('date').size().reindex(days, fill_value=0)
dailyH = ev[ev['sev']=='H'].groupby('date').size().reindex(days, fill_value=0)
out['n_days'] = len(days)
out['days_with_seizure_pct'] = float((daily>0).mean()*100)
out['daily_count_dist'] = {str(k): int(v) for k,v in daily.value_counts().sort_index().items()}
out['mean_per_day'] = float(daily.mean())
# by year
yr = ev.groupby(ev['date'].dt.year).agg(n=('date','size'), H=('sev', lambda s:(s=='H').sum()), med_dur=('dur_s','median'))
yr['days'] = [ (min(pd.Timestamp(f'{y}-12-31'), ev['date'].max()) - max(pd.Timestamp(f'{y}-01-01'), ev['date'].min())).days+1 for y in yr.index]
yr['per_day'] = yr['n']/yr['days']; yr['H_per_day']=yr['H']/yr['days']
out['by_year'] = yr.round(3).reset_index().to_dict('records')

# ---------- time of day ----------
t = ev[ev['hour'].notna()]
hour_all = t.groupby('hour').size().reindex(range(24), fill_value=0)
hour_H = t[t['sev']=='H'].groupby('hour').size().reindex(range(24), fill_value=0)
hour_L = t[t['sev']=='L'].groupby('hour').size().reindex(range(24), fill_value=0)
out['hour_all'] = hour_all.tolist(); out['hour_H']=hour_H.tolist(); out['hour_L']=hour_L.tolist()
# eras
eras = {'2019-2021': ('2019-01-01','2021-12-31'), '2022-2023': ('2022-01-01','2023-12-31'), '2024-2026': ('2024-01-01','2026-12-31')}
out['hour_by_era'] = {}
for k,(a,b) in eras.items():
    s = t[(t['date']>=a)&(t['date']<=b)]
    out['hour_by_era'][k] = s.groupby('hour').size().reindex(range(24), fill_value=0).tolist()
# share in windows
def share(s, lo, hi): return float(((s['hour']>=lo)&(s['hour']<hi)).mean()*100)
out['share_12_22_all'] = share(t,12,22); out['share_00_08_all']=share(t,0,8)
out['share_14_22_by_era'] = {k: share(t[(t['date']>=a)&(t['date']<=b)],14,22) for k,(a,b) in eras.items()}
out['peak_hours'] = hour_all.sort_values(ascending=False).head(5).to_dict()
# chi-square uniform
out['hour_chi2_p'] = float(stats.chisquare(hour_all.values).pvalue)

# ---------- day of week ----------
dow = ev.groupby(ev['date'].dt.dayofweek).size().reindex(range(7), fill_value=0)
out['dow'] = dow.tolist(); out['dow_chi2_p']=float(stats.chisquare(dow.values).pvalue)
dowH = ev[ev['sev']=='H'].groupby(ev[ev['sev']=='H']['date'].dt.dayofweek).size().reindex(range(7), fill_value=0)
out['dowH'] = dowH.tolist(); out['dowH_chi2_p']=float(stats.chisquare(dowH.values).pvalue)

# ---------- multidien cycle: Lomb-Scargle on daily counts (detrended) ----------
def periodogram(series, pmin=2, pmax=90):
    x = series.values.astype(float)
    x = x - pd.Series(x).rolling(91, center=True, min_periods=30).mean().bfill().ffill().values  # remove slow trend
    tt = np.arange(len(x))
    periods = np.linspace(pmin, pmax, 2000)
    freqs = 2*np.pi/periods
    pg = signal.lombscargle(tt, x - x.mean(), freqs, normalize=True)
    return periods, pg
periods, pg = periodogram(daily)
periodsH, pgH = periodogram(dailyH)
def top_peaks(periods, pg, n=6):
    idx, _ = signal.find_peaks(pg)
    top = sorted(idx, key=lambda i: -pg[i])[:n]
    return [(round(float(periods[i]),1), round(float(pg[i]),4)) for i in top]
out['periodogram_peaks_all'] = top_peaks(periods, pg)
out['periodogram_peaks_H'] = top_peaks(periodsH, pgH)
# significance by shuffling (permutation of daily counts within year)
rng = np.random.default_rng(0)
maxs=[]
for _ in range(200):
    sh = daily.copy()
    sh[:] = rng.permutation(daily.values)
    _, p2 = periodogram(sh)
    maxs.append(p2.max())
out['periodogram_perm_99'] = float(np.percentile(maxs, 99)); out['periodogram_perm_95']=float(np.percentile(maxs,95))
out['periodogram_max_all'] = float(pg.max())
# also per-era peaks
out['periodogram_by_era']={}
for k,(a,b) in eras.items():
    d = daily[(daily.index>=a)&(daily.index<=b)]
    p,g = periodogram(d)
    out['periodogram_by_era'][k] = top_peaks(p,g,4)
# autocorrelation of daily counts at lags 1..35
ac = [float(daily.autocorr(l)) for l in range(1,36)]
out['daily_autocorr'] = ac

# ---------- clustering / conditional risk ----------
# Probability of >=1 seizure tomorrow given today's count
df = pd.DataFrame({'n': daily, 'H': dailyH})
df['n_tom'] = df['n'].shift(-1); df['H_tom']=df['H'].shift(-1)
df['n_prev'] = df['n'].shift(1)
base_any = float((df['n_tom']>0).mean()); base_H = float((df['H_tom']>0).mean())
cond = {}
for k in [0,1,2,3]:
    sel = df['n']>=k if k==3 else df['n']==k
    lab = '3+' if k==3 else str(k)
    cond[lab] = dict(days=int(sel.sum()), p_any_tomorrow=float((df.loc[sel,'n_tom']>0).mean()), p_H_tomorrow=float((df.loc[sel,'H_tom']>0).mean()))
out['base_any_tomorrow']=base_any; out['base_H_tomorrow']=base_H; out['cond_by_today_count']=cond
# given H today
selH = df['H']>0
out['p_H_tomorrow_given_H_today'] = float((df.loc[selH,'H_tom']>0).mean()); out['n_H_days']=int(selH.sum())
out['p_H_tomorrow_given_noH_today'] = float((df.loc[~selH,'H_tom']>0).mean())
# given 7-day trailing rate
df['r7'] = df['n'].rolling(7).sum().shift(1)
df['r28'] = df['n'].rolling(28).sum().shift(1)/4
q = df.dropna(subset=['r7'])
q['r7bin'] = pd.cut(q['r7'], [-1,1,3,6,100], labels=['0-1','2-3','4-6','7+'])
out['p_any_today_by_r7'] = q.groupby('r7bin', observed=True).agg(days=('n','size'), p_any=('n', lambda s:(s>0).mean()), p_H=('H', lambda s:(s>0).mean())).reset_index().astype({'r7bin':str}).to_dict('records')
# trend ratio r7 vs r28
q['ratio'] = (q['r7']/7)/(q['r28']/7+0.05)
q['ratio_bin'] = pd.cut(q['ratio'], [0,0.5,1.0,1.5,100], labels=['<0.5','0.5-1','1-1.5','>1.5'])
out['p_any_today_by_ratio'] = q.groupby('ratio_bin', observed=True).agg(days=('n','size'), p_any=('n', lambda s:(s>0).mean()), p_H=('H', lambda s:(s>0).mean())).reset_index().astype({'ratio_bin':str}).to_dict('records')

# ---------- intra-day clustering ----------
t2 = ev[ev['ts'].notna()].sort_values('ts')
gaps_h = t2['ts'].diff().dt.total_seconds()/3600
out['gap_hours_quantiles'] = {str(k): float(v) for k,v in gaps_h.quantile([0.1,0.25,0.5,0.75,0.9]).items()}
out['pct_gaps_under_1h'] = float((gaps_h<1).mean()*100); out['pct_gaps_under_6h']=float((gaps_h<6).mean()*100)
# within-day: when day has >=2 seizures, hours apart median
md = t2.groupby('date').filter(lambda g: len(g)>=2)
intra = md.groupby('date')['ts'].apply(lambda s: s.diff().dt.total_seconds().dropna()/3600)
out['intra_day_gap_median_h'] = float(intra.median()); out['intra_day_gap_q25_h']=float(intra.quantile(.25)); out['intra_day_gap_q75_h']=float(intra.quantile(.75))
# severity escalation within day: given first seizure L, prob a later same-day seizure is H
first = t2.groupby('date').first();
multi = t2.groupby('date').filter(lambda g: len(g)>=2)
esc = multi.groupby('date').apply(lambda g: pd.Series({'first_sev': g.iloc[0]['sev'], 'later_H': (g.iloc[1:]['sev']=='H').any()}))
out['p_laterH_given_firstL'] = float(esc[esc['first_sev']=='L']['later_H'].mean()); out['p_laterH_given_firstH']=float(esc[esc['first_sev']=='H']['later_H'].mean())
out['n_multi_days']=int(len(esc))
# H seizure: hours since previous seizure
t2['gap_prev_h'] = gaps_h.values
out['gap_before_H_median_h'] = float(t2[t2['sev']=='H']['gap_prev_h'].median()); out['gap_before_L_median_h']=float(t2[t2['sev']=='L']['gap_prev_h'].median())
# after an H seizure, how long until the next seizure (recovery/refractory?)
t2['gap_next_h'] = (-t2['ts'].diff(-1)).dt.total_seconds()/3600
out['gap_after_H_median_h'] = float(t2[t2['sev']=='H']['gap_next_h'].median()); out['gap_after_L_median_h']=float(t2[t2['sev']=='L']['gap_next_h'].median())

# ---------- duration ----------
out['dur_quantiles_all'] = {str(k): float(v) for k,v in ev['dur_s'].quantile([.25,.5,.75,.9,.99]).items()}
out['dur_ge_120_pct'] = float((ev['dur_s']>=120).mean()*100); out['dur_ge_300_n']=int((ev['dur_s']>=300).sum())
out['dur_by_type'] = ev.groupby('type')['dur_s'].agg(['count','median','max']).round(0).reset_index().to_dict('records')
# duration trend by year for H
out['H_dur_median_by_year'] = ev[ev['sev']=='H'].groupby(ev['date'].dt.year)['dur_s'].median().to_dict()
# severity share by year
out['H_share_by_year'] = (ev.groupby(ev['date'].dt.year)['sev'].apply(lambda s:(s=='H').mean()*100)).round(1).to_dict()

# ---------- monthly series ----------
m = ev.groupby(ev['date'].dt.to_period('M')).agg(n=('date','size'), H=('sev', lambda s:(s=='H').sum()))
m.index = m.index.astype(str)
out['monthly'] = m.reset_index().to_dict('records')

# ---------- clobazam rescue ----------
c = ev[ev['clob'].notna() & (ev['clob']>0)]
out['n_rescue_rows'] = int(len(c)); out['rescue_date_range']=[str(c['date'].min().date()), str(c['date'].max().date())]
# next 3 days after rescue day vs matched days without rescue in same period
rd = set(c['date'].dt.normalize())
per = daily[(daily.index>=c['date'].min())&(daily.index<=c['date'].max())]
def next3(d): return float(daily[(daily.index>d)&(daily.index<=d+pd.Timedelta(days=3))].sum())
res = [next3(d) for d in rd]
nores = [next3(d) for d in per.index if d not in rd and daily[d]>0]
out['rescue_next3_mean'] = float(np.mean(res)); out['norescue_seizureday_next3_mean']=float(np.mean(nores))
out['rescue_sameday_mean'] = float(np.mean([daily[d] for d in rd])); out['norescue_seizureday_sameday_mean']=float(np.mean([daily[d] for d in per.index if d not in rd and daily[d]>0]))

# ---------- period flag ----------
p = ev[ev['period_start']]['date'].unique()
if len(p):
    win = [daily[(daily.index>=d)&(daily.index<=d+pd.Timedelta(days=3))].mean() for d in p]
    out['period_flag_days']=int(len(p)); out['period_0_3_mean_per_day']=float(np.mean(win)); out['overall_mean_per_day_same_years']=float(daily[(daily.index>=min(p))&(daily.index<=max(p))].mean())

json.dump(out, open('results.json','w'), indent=1, default=str)
print(json.dumps({k:v for k,v in out.items() if k not in ('monthly','daily_autocorr','hour_by_era')}, indent=1, default=str))
