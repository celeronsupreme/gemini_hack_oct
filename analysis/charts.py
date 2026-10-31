import pandas as pd, numpy as np, json
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.titlesize':13,'figure.dpi':150})
ev = pd.read_pickle('events.pkl'); r = json.load(open('results.json')); r2 = json.load(open('results2.json')); bt = json.load(open('backtest.json'))
BLUE='#2F6DB5'; RED='#C8452B'; GREY='#9AA3AD'; DARK='#2B2F36'; ORANGE='#E08A1E'

# 1. hour of day
fig, ax = plt.subplots(figsize=(9,4.2))
h = np.arange(24)
ax.bar(h, r['hour_L'], color=BLUE, label='Milder (quiet & aware, aura, etc.)')
ax.bar(h, r['hour_H'], bottom=r['hour_L'], color=RED, label='Severe (head to side / slack jaw / tonic-clonic)')
for x,lab in [(8,'08:00 am meds'),(19,'19:00 cenobamate'),(20.5,'20:00–21:00 pm meds')]:
    ax.axvline(x, color=GREY, ls=':', lw=1); ax.text(x+0.15, 60, lab, rotation=90, va='bottom', ha='left', fontsize=8, color=DARK)
ax.set_xticks(h); ax.set_xticklabels([f'{i:02d}' for i in h], fontsize=8)
ax.set_xlabel('Hour of day (start time)'); ax.set_ylabel('Seizures, Jul 2018–Aug 2026')
ax.set_title('Seizures by hour of day: 75% start between midday and 22:00, peaking at 19:00')
ax.legend(frameon=False, loc='upper left', fontsize=9); ax.set_ylim(0, max(r['hour_all'])*1.15)
fig.tight_layout(); fig.savefig('chart_hour_of_day.png'); plt.close(fig)

# 2. monthly timeline with medication markers
m = pd.DataFrame(r['monthly']); m['date']=pd.PeriodIndex(m['date'], freq='M').to_timestamp()
m = m[m['date']>='2018-08-01']
fig, ax = plt.subplots(figsize=(11,4.4))
ax.bar(m['date'], m['n'], width=25, color=BLUE, label='All seizures per month')
ax.bar(m['date'], m['H'], width=25, color=RED, label='Severe per month')
marks = [('2018-12-19','Clobazam daily'),('2020-02-17','Clobazam stopped'),('2020-06-20','Keto diet'),('2020-12-18','VNS implanted'),('2022-11-29','Brivaracetam'),('2023-02-17','Cenobamate start'),('2024-07-21','Oxcarbazepine stopped'),('2025-10-09','Briv. pm shift')]
for d,lab in marks:
    d=pd.Timestamp(d); ax.axvline(d, color=DARK, lw=0.8, ls='--', alpha=.6); ax.text(d, m['n'].max()*1.02, lab, rotation=90, va='bottom', ha='right', fontsize=8, color=DARK)
ax.set_ylim(0, m['n'].max()*1.5); ax.set_ylabel('Seizures per month'); ax.legend(frameon=False, loc='upper left', fontsize=9)
ax.set_title('Seizures per month, with the main treatment changes', fontsize=12)
fig.tight_layout(); fig.savefig('chart_monthly_timeline.png'); plt.close(fig)

# 3. clustering: P(any tomorrow | today count) and P(any today | 7-day count)
fig, axes = plt.subplots(1,2, figsize=(10,3.8))
c = r['cond_by_today_count']; labs=['0','1','2','3+']
ax=axes[0]; ax.bar(labs, [c[k]['p_any_tomorrow']*100 for k in labs], color=BLUE)
ax.axhline(r['base_any_tomorrow']*100, color=GREY, ls=':', lw=1); ax.text(3.45, r['base_any_tomorrow']*100+1, f"all days {r['base_any_tomorrow']*100:.0f}%", fontsize=8, color=GREY, ha='right')
for i,k in enumerate(labs): ax.text(i, c[k]['p_any_tomorrow']*100+1.5, f"{c[k]['p_any_tomorrow']*100:.0f}%", ha='center', fontsize=9)
ax.set_xlabel('Seizures today'); ax.set_ylabel('% chance of ≥1 seizure tomorrow'); ax.set_ylim(0,90); ax.set_title('More today → more likely tomorrow')
q = pd.DataFrame(r['p_any_today_by_r7']); ax=axes[1]
ax.bar(q['r7bin'], q['p_any']*100, color=BLUE, label='any seizure'); ax.bar(q['r7bin'], q['p_H']*100, color=RED, width=0.4, label='severe seizure')
for i,v in enumerate(q['p_any']*100): ax.text(i, v+1.5, f"{v:.0f}%", ha='center', fontsize=9)
ax.set_xlabel('Seizures in the previous 7 days'); ax.set_ylabel('% chance of a seizure today'); ax.set_ylim(0,90); ax.legend(frameon=False, fontsize=9); ax.set_title('A quiet week really is quieter')
fig.tight_layout(); fig.savefig('chart_clustering.png'); plt.close(fig)

# 4. era shift in hour profile (normalised)
fig, ax = plt.subplots(figsize=(9,3.8))
for k,col in [('2019-2021',GREY),('2024-2026',RED)]:
    v=np.array(r['hour_by_era'][k], float); v=v/v.sum()*100
    ax.plot(h, v, marker='o', ms=3, color=col, label=f"{k} (n={int(np.array(r['hour_by_era'][k]).sum())})")
ax.set_xticks(h); ax.set_xticklabels([f'{i:02d}' for i in h], fontsize=8); ax.set_ylabel('% of that era\'s seizures'); ax.set_xlabel('Hour of day')
ax.set_title('The evening peak has sharpened: 14:00–22:00 held 52% of seizures in 2019–21, 78% in 2024–26', fontsize=11)
ax.legend(frameon=False, fontsize=9); fig.tight_layout(); fig.savefig('chart_era_shift.png'); plt.close(fig)

# 5. backtest tiers
fig, axes = plt.subplots(1,2, figsize=(10,3.8))
for ax,(key,title,ylab) in zip(axes, [('y_any3','Any seizure in the next 3 hours','% of hours followed by a seizure within 3 h'),('y_H6','Severe seizure in the next 6 hours','% of hours followed by a severe seizure within 6 h')]):
    t = pd.DataFrame(bt[key]['tiers']).set_index('tier').loc[['low','medium','high']]
    cols=[BLUE,ORANGE,RED]
    ax.bar(['Low\n(50% of hours)','Medium\n(35%)','High\n(15%)'], t['pos_rate']*100, color=cols)
    for i,v in enumerate(t['pos_rate']*100): ax.text(i, v+0.5, f"{v:.1f}%", ha='center', fontsize=10)
    ax.axhline(bt[key]['base_rate']*100, color=GREY, ls=':', lw=1); ax.text(2.4, bt[key]['base_rate']*100+0.5, f"average {bt[key]['base_rate']*100:.1f}%", fontsize=8, color=GREY, ha='right')
    ax.set_title(title, fontsize=11); ax.set_ylabel(ylab, fontsize=9)
fig.suptitle('Backtest of a three-tier risk indicator, trained on 2019–2023, tested on 2024–Aug 2026', fontweight='bold', fontsize=12)
fig.tight_layout(); fig.savefig('chart_backtest_tiers.png'); plt.close(fig)

# 6. notes themes: severe share
th = pd.DataFrame(r2['notes_themes']); th = th[th['n_notes']>=15].sort_values('H_share_pct', ascending=True)
fig, ax = plt.subplots(figsize=(9,4.6))
colors=[RED if v>r2['notes_H_share_overall']+8 else (BLUE if v<r2['notes_H_share_overall']-8 else GREY) for v in th['H_share_pct']]
ax.barh(th['theme'], th['H_share_pct'], color=colors)
ax.axvline(r2['notes_H_share_overall'], color=DARK, ls='--', lw=1); ax.text(r2['notes_H_share_overall']+0.5, -0.6, f"all noted seizures: {r2['notes_H_share_overall']}% severe", fontsize=8, color=DARK)
for i,(v,n) in enumerate(zip(th['H_share_pct'], th['n_notes'])): ax.text(v+0.8, i, f"{v:.0f}%  (n={n})", va='center', fontsize=8)
ax.set_xlabel('% of noted seizures that were severe'); ax.set_xlim(0,80)
ax.set_title('Severe-seizure share by what the carer\'s note mentioned', fontsize=12)
fig.tight_layout(); fig.savefig('chart_notes_themes.png'); plt.close(fig)
print('ok')
