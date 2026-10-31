import pandas as pd, numpy as np, json, re
from scipy import stats
ev = pd.read_pickle('events.pkl')
allrows = pd.read_pickle('all_rows.pkl')
days = pd.date_range(ev['date'].min(), ev['date'].max(), freq='D')
daily = ev.groupby('date').size().reindex(days, fill_value=0)
dailyH = ev[ev['sev']=='H'].groupby('date').size().reindex(days, fill_value=0)
out = {}

# ---------- medication era windows ----------
events = [
 ('Lamotrigine start', '2018-07-26'), ('Carbamazepine start / lamotrigine taper', '2018-10-02'),
 ('Clobazam daily 5 mg (restart)', '2018-12-02'), ('Clobazam taper 5 to 4 mg', '2019-01-28'),
 ('Carbamazepine to oxcarbazepine', '2019-12-29'), ('Clobazam daily stopped', '2020-02-17'),
 ('Keto diet start', '2020-06-20'), ('Oxcarbazepine up to 1200/1200', '2021-10-18'),
 ('Oxcarbazepine split to 3 doses (7am/2pm/9pm)', '2021-11-06'),
 ('Levetiracetam to brivaracetam', '2022-11-29'), ('Cenobamate start 12.5 mg', '2023-02-17'),
 ('Cenobamate reaches 200 mg', '2023-04-28'), ('Cenobamate 350 mg', '2023-10-25'),
 ('Cenobamate 400 mg', '2024-03-29'), ('Oxcarbazepine stopped', '2024-07-21'),
 ('Cenobamate back to 350 mg', '2024-10-19'), ('Brivaracetam 100/100/50 (more daytime)', '2025-01-09'),
 ('Cenobamate 300 mg', '2025-03-05'), ('Cenobamate 350 mg (seizures up)', '2025-03-16'),
 ('Brivaracetam back to 100/50/100', '2025-06-09'), ('Brivaracetam 100/0/150 (afternoon dose moved to evening)', '2025-10-09'),
]
rows=[]
for name, d in events:
    d = pd.Timestamp(d)
    pre = daily[(daily.index>=d-pd.Timedelta(days=56))&(daily.index<d)]
    post = daily[(daily.index>=d)&(daily.index<d+pd.Timedelta(days=56))]
    preH = dailyH[pre.index]; postH = dailyH[post.index]
    if len(pre)<28 or len(post)<28: continue
    # Poisson rate test (approx via chi-square on totals)
    p = stats.poisson_means_test(int(pre.sum()), len(pre), int(post.sum()), len(post)).pvalue
    rows.append(dict(change=name, date=str(d.date()), pre_per_wk=round(pre.mean()*7,2), post_per_wk=round(post.mean()*7,2), preH_per_wk=round(preH.mean()*7,2), postH_per_wk=round(postH.mean()*7,2), p=round(float(p),3)))
out['med_eras'] = rows
pd.DataFrame(rows).to_csv('med_eras.csv', index=False)
print(pd.DataFrame(rows).to_string())

# ---------- hour profile before/after 9 Oct 2025 (afternoon brivaracetam dose moved to evening) ----------
t = ev[ev['hour'].notna()]
pre = t[(t['date']>='2025-01-01')&(t['date']<'2025-10-09')]
post = t[(t['date']>='2025-10-09')]
def prof(s): return s.groupby('hour').size().reindex(range(24), fill_value=0)
out['hour_pre_oct25'] = prof(pre).tolist(); out['hour_post_oct25']=prof(post).tolist()
out['n_pre_oct25']=len(pre); out['n_post_oct25']=len(post)
out['share_14_19_pre']=float(((pre['hour']>=14)&(pre['hour']<19)).mean()); out['share_14_19_post']=float(((post['hour']>=14)&(post['hour']<19)).mean())
out['share_19_23_pre']=float(((pre['hour']>=19)&(pre['hour']<23)).mean()); out['share_19_23_post']=float(((post['hour']>=19)&(post['hour']<23)).mean())
out['per_day_pre_oct25']=float(len(pre)/((pd.Timestamp('2025-10-09')-pd.Timestamp('2025-01-01')).days)); out['per_day_post_oct25']=float(len(post)/((ev['date'].max()-pd.Timestamp('2025-10-09')).days+1))
print('oct25 shift:', {k:out[k] for k in ['n_pre_oct25','n_post_oct25','share_14_19_pre','share_14_19_post','share_19_23_pre','share_19_23_post','per_day_pre_oct25','per_day_post_oct25']})

# hour profile relative to scheduled evening dose per era: 2019-2021 evening dose 20:00; 2024+: cenobamate 19:00, briv 21:00
# ---------- notes mining ----------
notes = ev[ev['notes'].str.len()>0].copy()
kw = {
 'stress/upset/anxiety': r'upset|stress|anxi|row |argument|cry|crying|angry|worried|nervous|excit|emotion',
 'tired/sleep': r'tired|exhaust|sleep|late night|up since|woke|nap|asleep|bed',
 'hot/heat/shower/bath': r'\bhot\b|heat|shower|bath|warm|sweat|temperature',
 'cold': r'\bcold\b|freezing|chilly',
 'illness/unwell': r'\bill\b|unwell|sick|cold\b|cough|temperature|fever|headache|migraine|pain|hurt|vomit|nausea|bug',
 'period/menstrual': r'period|menstru',
 'exercise/activity': r'walk|exercise|gym|trampoline|run|swim|bike|cycling|weights|dance|sport',
 'school/lesson': r'school|lesson|class|homework|exam|college',
 'food/hunger/sugar': r'hungry|food|eat|ate|sugar|ketone|keto|glucose|meal|dinner|lunch|breakfast',
 'medication mentioned': r'\bmg\b|dose|clobazam|keppra|levetir|oxcarb|carbam|cenob|brivar|lamotri|lacosam|midaz|medication|meds',
 'aura / felt it coming': r'felt funny|feel funny|felt it|feeling|aura|coming|warning|funny|going funny',
 'screen/tv/lights': r'tv|screen|phone|lights|flash|film|movie|ipad',
 'travel/car/train': r'\bcar\b|train|driving|bus|journey|flight|travel',
 'alarm button pressed': r'alarm|button|pressed|buzzer',
 'missed/late dose': r'missed|forgot|late dose|late meds|hadn.t taken|not taken|didn.t take|no meds',
}
rows=[]
for k,pat in kw.items():
    m = notes['notes'].str.contains(pat, case=False, regex=True)
    sub = notes[m]
    rows.append(dict(theme=k, n_notes=int(m.sum()), pct_of_notes=round(m.mean()*100,1), H_share_pct=round((sub['sev']=='H').mean()*100,1) if len(sub) else None, median_dur_s=float(sub['dur_s'].median()) if len(sub) else None))
out['notes_themes'] = rows
out['notes_H_share_overall'] = round((notes['sev']=='H').mean()*100,1)
out['notes_n'] = len(notes)
print(pd.DataFrame(rows).to_string())
print('H share among noted events overall', out['notes_H_share_overall'])

# sample notes per theme for the doc (short)
samples={}
for k,pat in kw.items():
    m = notes['notes'].str.contains(pat, case=False, regex=True)
    samples[k] = [ (str(r['date'].date()), r['notes'][:140]) for _,r in notes[m].sample(min(4,int(m.sum())), random_state=3).iterrows()]
out['note_samples']=samples

# explicit trigger statements by the family
trig = notes[notes['notes'].str.contains(r'trigger', case=False)]
out['explicit_trigger_notes'] = [(str(r['date'].date()), r['notes'][:200]) for _,r in trig.iterrows()]
print('\nEXPLICIT TRIGGER NOTES', len(trig))
for d,n in out['explicit_trigger_notes']: print(d, n)

# VNS mentions
vns = allrows[allrows['notes'].str.contains('VNS', case=False)]
print('\nVNS mentions:');
for _,r in vns.iterrows(): print(r['date'].date(), r['notes'][:200])
# tonic-clonic dates
print('\nTonic-clonic:', ev[ev['type']=='Tonic-clonic']['date'].dt.date.tolist())
print('>=5min events:', ev[ev['dur_s']>=300][['date','dur_s','type']].to_string())

json.dump(out, open('results2.json','w'), indent=1, default=str)
