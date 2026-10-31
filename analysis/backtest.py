import pandas as pd, numpy as np, json
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score, brier_score_loss
ev = pd.read_pickle('events.pkl')
t = ev[ev['ts'].notna()].sort_values('ts')
start, end = pd.Timestamp('2019-01-01'), t['ts'].max().normalize()
hours = pd.date_range(start, end + pd.Timedelta(hours=23), freq='h')
# counts per hour
hc = t.groupby(t['ts'].dt.floor('h')).size().reindex(hours, fill_value=0)
hH = t[t['sev']=='H'].groupby(t[t['sev']=='H']['ts'].dt.floor('h')).size().reindex(hours, fill_value=0)
df = pd.DataFrame({'n': hc, 'H': hH})
df['hour'] = df.index.hour; df['dow']=df.index.dayofweek
# trailing features (exclude current hour)
for w,name in [(24,'n24'),(24*7,'n7d'),(24*28,'n28d')]:
    df[name] = df['n'].rolling(w).sum().shift(1).fillna(0)
df['H24'] = df['H'].rolling(24).sum().shift(1).fillna(0)
df['n_today'] = df.groupby(df.index.date)['n'].cumsum() - df['n']
df['hrs_since_last'] = np.nan
last = None; hs=[]
for ts, n in zip(df.index, df['n']):
    hs.append((ts-last).total_seconds()/3600 if last is not None else 999)
    if n>0: last = ts
df['hrs_since_last'] = np.minimum(hs, 999)
# targets: any seizure in next 3h, H in next 6h, any seizure in next 24h
df['y_any3'] = (df['n'].rolling(3).sum().shift(-3).fillna(0)>0).astype(int)
df['y_H6'] = (df['H'].rolling(6).sum().shift(-6).fillna(0)>0).astype(int)
df['y_any24'] = (df['n'].rolling(24).sum().shift(-24).fillna(0)>0).astype(int)
df['hour_sin']=np.sin(2*np.pi*df['hour']/24); df['hour_cos']=np.cos(2*np.pi*df['hour']/24)
feats = ['hour_sin','hour_cos','n24','n7d','n28d','H24','n_today','hrs_since_last','dow']
train = df[df.index < '2024-01-01']; test = df[df.index >= '2024-01-01']
out={}
for y in ['y_any3','y_H6','y_any24']:
    base = test[y].mean()
    res = {'base_rate': float(base)}
    # model 1: hour only
    m0 = LogisticRegression(max_iter=1000).fit(train[['hour_sin','hour_cos']], train[y])
    p0 = m0.predict_proba(test[['hour_sin','hour_cos']])[:,1]
    res['auc_hour_only'] = float(roc_auc_score(test[y], p0))
    # model 2: recent history only
    m1 = LogisticRegression(max_iter=1000).fit(train[['n24','n7d','n28d','H24','n_today','hrs_since_last']], train[y])
    p1 = m1.predict_proba(test[['n24','n7d','n28d','H24','n_today','hrs_since_last']])[:,1]
    res['auc_history_only'] = float(roc_auc_score(test[y], p1))
    # model 3: all, gradient boosting
    m2 = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_depth=4, categorical_features=[feats.index('dow')]).fit(train[feats], train[y])
    p2 = m2.predict_proba(test[feats])[:,1]
    res['auc_all_gbm'] = float(roc_auc_score(test[y], p2)); res['brier_gbm']=float(brier_score_loss(test[y], p2)); res['brier_base']=float(brier_score_loss(test[y], np.full(len(test), train[y].mean())))
    # three-tier: thresholds so that high = top 15% of hours, medium = next 35%, low = bottom 50%
    q85, q50 = np.quantile(p2, [0.85, 0.50])
    tier = np.where(p2>=q85,'high', np.where(p2>=q50,'medium','low'))
    tt = test.assign(tier=tier)
    # share of target-positive hours (events) captured in each tier
    evcol = 'n' if y!='y_H6' else 'H'
    # count actual events that occur in the forecast window starting at each hour: approximate by events in the hour itself labelled by tier of that hour
    caps = tt.groupby('tier').agg(hours_pct=('n', lambda s: len(s)/len(tt)*100), events=(evcol,'sum'), pos_rate=(y,'mean'))
    caps['events_pct'] = caps['events']/caps['events'].sum()*100
    res['tiers'] = caps.round(3).reset_index().to_dict('records')
    out[y]=res
    print(y, json.dumps(res, indent=1))
# feature importance proxy: AUC drop
json.dump(out, open('backtest.json','w'), indent=1)
# also a transparent points-based score for the doc: compute AUC of a hand rule on test
def rule(r):
    s=0
    s += {0:0,1:1,2:2}.get(int(min(r['n_today'],2)),0)*1.0
    s += 1.0 if r['n7d']>=7 else (0.5 if r['n7d']>=4 else 0)
    s += 1.0 if 17<=r['hour']<=21 else (0.5 if 12<=r['hour']<17 or r['hour']==22 else 0)
    s += 0.5 if r['hrs_since_last']<6 else 0
    return s
test = test.copy(); test['rule']=test.apply(rule, axis=1)
for y in ['y_any3','y_H6','y_any24']:
    print('hand rule AUC', y, round(roc_auc_score(test[y], test['rule']),3))
