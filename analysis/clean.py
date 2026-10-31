import pandas as pd, numpy as np, re, datetime as dt
df = pd.read_pickle('seizures_raw.pkl')
df = df[df['Date'].notna()].copy()
df['date'] = pd.to_datetime(df['Date']).dt.normalize()

def to_time(t):
    if isinstance(t, dt.time): return t
    if isinstance(t, dt.datetime): return t.time()
    if isinstance(t, str):
        m = re.match(r'^\s*(\d{1,2}):(\d{2})', t)
        if m: return dt.time(int(m.group(1)), int(m.group(2)))
    return None
df['time'] = df['Time'].apply(to_time)
df['ts'] = [pd.Timestamp.combine(d, t) if t is not None else pd.NaT for d, t in zip(df['date'], df['time'])]
df['hour'] = df['ts'].dt.hour
df['dur_s'] = pd.to_numeric(df['Duration seconds (Calc)'], errors='coerce')
df['sev'] = df['Seizure Severity (H/L)'].where(df['Seizure Severity (H/L)'].isin(['H', 'L']))

def norm_type(t):
    if not isinstance(t, str) or not t.strip(): return 'Unlabelled'
    raw = t
    first = t.split('#')[0].strip().lower()
    unsure = 'unsure' in t.lower()
    if 'tonic' in first: return 'Tonic-clonic'
    if first.startswith('head'): return 'Head to side, saliva, cannot speak'
    if 'slack' in first: return 'Slack jaw, dribbling'
    if 'quiet and aware' in first: return 'Quiet and aware'
    if 'very short' in first or 'aura' in first: return 'Aura / aborted start'
    if 'scared' in first: return 'Looking scared, mouth to side'
    if 'talk' in first: return "Couldn't talk properly"
    if 'absence' in first: return 'Absence'
    if 'deja' in first or 'déj' in first: return 'Deja vu'
    if 'non epileptic' in first or 'nes' in first: return 'Non-epileptic (NES)'
    if 'simple partial' in first or 'epileptic' in first: return 'Other'
    if 'unsure' in first: return 'Unsure'
    return 'Other'
df['type'] = df['Type'].apply(norm_type)
df['unsure'] = df['Type'].astype(str).str.lower().str.contains('unsure')
df['notes'] = df['Notes'].where(df['Notes'].notna(), '').astype(str).str.strip()
df['clob'] = pd.to_numeric(df['Clobazam Dose (10mg)'], errors='coerce')
df['period_start'] = df['Day One of Period'].astype(str).str.strip().str.lower().eq('x')
df['is_seizure'] = df['Seizure Date'].notna()
ev = df[df['is_seizure']].copy()
ev = ev.sort_values(['date', 'ts']).reset_index(drop=True)
ev.to_pickle('events.pkl')
df.to_pickle('all_rows.pkl')
print('events', len(ev), 'with time', ev['ts'].notna().sum(), 'range', ev['date'].min().date(), ev['date'].max().date())
print(ev['type'].value_counts())
print(pd.crosstab(ev['type'], ev['sev']))
print(ev.groupby('type')['dur_s'].median())
