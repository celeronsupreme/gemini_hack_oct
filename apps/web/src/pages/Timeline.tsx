// Eight years on one screen: hour-of-day histogram, monthly bars with medication changes, and a replay scrubber that
// calls /risk/now?at= so a real day can be stepped through hour by hour.
import { useEffect, useState } from 'react';
import { useStore } from '@/state/store';
import { HourHistogram, MonthlyBars } from '@/components/Charts';
import { RiskTile } from '@/components/RiskTile';

const REPLAY_DAYS = [
  { label: '29 Jan 2019 — cluster after a clobazam taper', date: '2019-01-29' },
  { label: '10 Mar 2025 — the week a cenobamate cut was reversed', date: '2025-03-10' },
  { label: '21 Aug 2026 — a recent evening', date: '2026-08-21' },
];

export function Timeline() {
  const { hourly, monthly, risk, loadTimeline, setRiskAt } = useStore();
  const [day, setDay] = useState(REPLAY_DAYS[2].date);
  const [hour, setHour] = useState(18);
  const [replaying, setReplaying] = useState(false);
  useEffect(() => { void loadTimeline(); }, [loadTimeline]);
  useEffect(() => { if (replaying) void setRiskAt(`${day}T${String(hour).padStart(2, '0')}:00:00`); }, [replaying, day, hour, setRiskAt]);

  return (
    <div className="screen">
      <h1>Patterns</h1>
      {hourly && (
        <div className="card">
          <b>By hour of day</b>
          <div className="muted">{hourly.total} seizures in the last year · {hourly.share_12_22_pct}% start between midday and 22:00 · peak {hourly.peak_hour !== null ? `${String(hourly.peak_hour).padStart(2, '0')}:00` : '—'}</div>
          <HourHistogram data={hourly} highlightHour={replaying ? hour : undefined} />
          <div className="legend"><span><i style={{ background: 'var(--accent)' }} />mild</span><span><i style={{ background: 'var(--high)' }} />severe</span><span>┆ scheduled dose</span></div>
        </div>
      )}
      {monthly && (
        <div className="card">
          <b>By month</b>
          <div className="muted">Dashed lines mark medication starts, stops and changes with a clear effect.</div>
          <MonthlyBars data={monthly} />
          <details>
            <summary className="muted">Medication changes with before/after rates</summary>
            <table style={{ width: '100%', fontSize: 12, marginTop: 8 }}>
              <tbody>
                {monthly.medication_changes.slice().reverse().map((c, i) => (
                  <tr key={i}><td>{c.date}</td><td>{c.drug} {c.action}</td><td>{c.before_per_week ?? '—'} → {c.after_per_week ?? '—'}/wk</td><td><span className="chip">{c.verdict}</span></td></tr>
                ))}
              </tbody>
            </table>
          </details>
        </div>
      )}
      <div className="card">
        <div className="row"><b className="grow">Replay a day</b><button className="btn ghost" onClick={() => { setReplaying(!replaying); if (replaying) void setRiskAt(undefined); }}>{replaying ? 'Back to now' : 'Start replay'}</button></div>
        <select value={day} onChange={(e) => setDay(e.target.value)}>{REPLAY_DAYS.map((d) => <option key={d.date} value={d.date}>{d.label}</option>)}</select>
        <input type="date" value={day} onChange={(e) => setDay(e.target.value)} style={{ marginTop: 6 }} />
        <input className="scrub" type="range" min={0} max={23} value={hour} onChange={(e) => setHour(Number(e.target.value))} />
        <div className="muted">Hour: {String(hour).padStart(2, '0')}:00</div>
      </div>
      {replaying && <RiskTile risk={risk} replayAt={`${day}T${String(hour).padStart(2, '0')}:00:00`} />}
    </div>
  );
}
