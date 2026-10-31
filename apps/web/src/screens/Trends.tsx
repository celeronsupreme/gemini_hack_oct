// Trends, pushed from the Today card: last 7 days vs her usual, time of day, by month with medication changes,
// and the trigger lab's ladder. Every number here comes from the engine (/stats/*, /triggers).
import { useEffect, useState } from 'react';
import type { MedicationChange, MonthlyStats, TriggerTest } from '@seizure/contracts';
import { herOf, useStore } from '@/state/store';
import { RUNG_COLORS, RUNG_LABEL } from '@/ui/catalogue';
import { daysAgo, h12, MON, MONTH } from '@/ui/format';

const ACTION: Record<string, string> = { decrease: 'lowered', increase: 'raised', start: 'started', stop: 'stopped', change: 'changed', taper: 'tapered', surgery: 'surgery', ongoing: 'continued' };
const ym = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;

export function Trends() {
  const { screen, year, baseline, hourly, monthly, triggers, profile, go, loadTrends } = useStore();
  const visible = screen === 'trends';
  useEffect(() => { if (visible) void loadTrends(); }, [visible, loadTrends]);
  const her = herOf(profile);
  return (
    <div className="screen pushed scr" style={{ zIndex: 10, transform: visible ? 'none' : 'translateX(100%)' }}>
      <div style={{ padding: '6px 12px 0' }}><button className="back" onClick={() => go('home')}><span>‹</span>Today</button></div>
      <div className="large-title">Trends</div>
      <Week year={year} usualPerWeek={baseline?.weekly_median ?? null} her={her} />
      {hourly && (
        <div className="card" style={{ margin: '0 16px 12px' }}>
          <Head title="Time of day" right="Last 12 months" />
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 6 }}>
            <span className="big-num">{hourly.peak_hour != null ? h12(hourly.peak_hour) : '—'}</span><span className="big-unit">busiest hour</span>
          </div>
          <div style={{ height: 100, marginTop: 12, display: 'flex', alignItems: 'flex-end', gap: 3, borderBottom: '1px solid rgba(60,60,67,.22)' }}>
            {hourly.by_hour.map((b) => { const max = Math.max(1, ...hourly.by_hour.map((x) => x.all)); return (
              <div key={b.hour} title={`${b.all} at ${h12(b.hour)}`} style={{ flex: 1, height: `${Math.max(2, b.all / max * 100)}%`, background: b.hour === hourly.peak_hour ? 'var(--blue)' : 'var(--blue-mid)', borderRadius: '3px 3px 1px 1px' }} />); })}
          </div>
          <Axis labels={['00:00', '06:00', '12:00', '18:00']} />
          <div style={{ marginTop: 12, fontSize: 14, lineHeight: 1.4, color: 'var(--ink-2)' }}>
            {hourly.total ? `${Math.round(hourly.share_12_22_pct)}% of ${her} seizures happen between midday and 10 pm.` : `No seizures logged in the last 12 months.`}
          </div>
        </div>
      )}
      {monthly && <Months monthly={monthly} her={her} />}
      <Triggers triggers={triggers} />
      <div className="footnote">Patterns from {her} own diary, not medical advice. Research prototype.</div>
    </div>
  );
}

const Head = ({ title, right }: { title: string; right: string }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ fontSize: 15, fontWeight: 600, color: 'var(--blue)' }}>{title}</span><span style={{ fontSize: 14, color: 'var(--ink-3)' }}>{right}</span></div>
);
const Axis = ({ labels }: { labels: string[] }) => (
  <div style={{ position: 'relative', height: 16, marginTop: 6, fontSize: 12, fontWeight: 500, color: '#48484A' }}>
    {labels.map((l, i) => <span key={l} style={{ position: 'absolute', left: `${i * 25}%`, transform: i ? 'translateX(-50%)' : 'none' }}>{l}</span>)}
  </div>
);

function Week({ year, usualPerWeek, her }: { year: { start_time: string }[]; usualPerWeek: number | null; her: string }) {
  const days = [6, 5, 4, 3, 2, 1, 0].map((n) => daysAgo(n));
  const counts = days.map((d) => { const next = new Date(d); next.setDate(d.getDate() + 1); return year.filter((e) => { const t = new Date(e.start_time); return t >= d && t < next; }).length; });
  const usual = usualPerWeek != null ? usualPerWeek / 7 : null;
  const max = Math.max(3, ...counts, usual ?? 0);
  const first = days[0], last = days[6];
  const range = first.getMonth() === last.getMonth() ? `${first.getDate()}–${last.getDate()} ${MON[last.getMonth()]}` : `${first.getDate()} ${MON[first.getMonth()]} – ${last.getDate()} ${MON[last.getMonth()]}`;
  return (
    <div className="card" style={{ margin: '0 16px 12px' }}>
      <Head title="Last 7 days" right={range} />
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 6 }}>
        <span className="big-num">{counts.reduce((a, b) => a + b, 0)}</span><span className="big-unit">this week</span>
        {usual != null && <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 500, color: 'var(--ink-3)' }}><span style={{ width: 16, borderTop: '1.5px dashed rgba(60,60,67,.45)' }} />{her} usual</span>}
      </div>
      <div style={{ position: 'relative', height: 110, marginTop: 12, display: 'flex', alignItems: 'flex-end', gap: 10, borderBottom: '1px solid rgba(60,60,67,.22)' }}>
        {usual != null && <div style={{ position: 'absolute', left: 0, right: 0, bottom: `${usual / max * 100}%`, borderTop: '1.5px dashed rgba(60,60,67,.35)' }} />}
        {counts.map((c, i) => <div key={i} title={`${c}`} style={{ flex: 1, height: `${Math.max(3, c / max * 100)}%`, background: i === 6 ? 'var(--blue)' : 'var(--blue-mid)', borderRadius: '6px 6px 2px 2px' }} />)}
      </div>
      <div style={{ display: 'flex', gap: 10, marginTop: 6 }}>
        {days.map((d, i) => <span key={i} style={{ flex: 1, textAlign: 'center', fontSize: 12, fontWeight: i === 6 ? 700 : 500, color: '#48484A' }}>{i === 6 ? 'Today' : 'SMTWTFS'[d.getDay()]}</span>)}
      </div>
    </div>
  );
}

/** Medication changes worth a marker: one per month, the first change that month, with a before/after verdict. */
function notable(changes: MedicationChange[]): MedicationChange[] {
  const seen = new Set<string>();
  return changes.filter((c) => c.verdict && !/too early|no clear/.test(c.verdict) && ['decrease', 'increase', 'start', 'stop', 'change', 'taper'].includes(c.action))
    .filter((c) => { const m = c.date.slice(0, 7); if (seen.has(m)) return false; seen.add(m); return true; });
}

/** The last 12 calendar months ending this month. Tap a bar to see that month; numbered badges mark medication changes. */
function Months({ monthly, her }: { monthly: MonthlyStats; her: string }) {
  const now = new Date();
  const keys = Array.from({ length: 12 }, (_, i) => ym(new Date(now.getFullYear(), now.getMonth() - (11 - i), 1)));
  const [sel, setSel] = useState(keys[11]);
  const stat = new Map(monthly.months.map((m) => [m.month, m]));
  const counts = keys.map((k) => stat.get(k)?.all ?? 0);
  const max = Math.max(1, ...counts);
  const shown = notable(monthly.medication_changes).filter((c) => keys.includes(c.date.slice(0, 7)));
  const markOf = new Map(shown.map((c, i) => [c.date.slice(0, 7), i + 1]));
  const name = (k: string) => { const [y, m] = k.split('-').map(Number); return y === now.getFullYear() ? MONTH[m - 1] : `${MONTH[m - 1]} ${y}`; };
  const short = (k: string) => { const [y, m] = k.split('-').map(Number); return `${MON[m - 1]} ${y}`; };
  const sentence = (c: MedicationChange) => {
    const b = c.before_per_week, a = c.after_per_week;
    if (/too early/.test(c.verdict)) return 'Too early to tell what changed.';
    if (/rise|fall/.test(c.verdict) && b != null && a != null) return `${/probable/.test(c.verdict) ? 'Probably' : 'Clearly'} ${/rise/.test(c.verdict) ? 'up' : 'down'} afterwards: ${b.toFixed(1)} → ${a.toFixed(1)} a week.`;
    return `Within ${her} usual range afterwards.`;
  };

  // The selected month against her usual month: the median of the 12 months with data before it.
  const m = stat.get(sel);
  const before = monthly.months.filter((x) => x.month < sel).slice(-12).map((x) => x.all).sort((a, b) => a - b);
  const usual = before.length >= 3 ? before[Math.floor(before.length / 2)] : null;
  const n = m?.all ?? 0;
  const [sy, sm] = sel.split('-').map(Number);
  const isNow = sel === keys[11];
  const daysIn = isNow ? now.getDate() : new Date(sy, sm, 0).getDate();
  const compare = usual == null || !m ? null : n > usual * 1.15 ? `More than ${her} usual month (${usual})` : n < usual * 0.85 ? `Fewer than ${her} usual month (${usual})` : `About ${her} usual month (${usual})`;
  const changes = monthly.medication_changes.filter((c) => c.date.startsWith(sel));

  return (
    <div className="card" style={{ margin: '0 16px 12px' }}>
      <Head title="By month" right={`${short(keys[0])} – ${short(keys[11])}`} />
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 6 }}>
        <span className="big-num">{n}</span><span className="big-unit">in {name(sel)}{isNow ? ' so far' : ''}</span>
      </div>
      <div role="group" aria-label="Seizures per month; tap a month for details" style={{ height: 120, marginTop: 14, display: 'flex', alignItems: 'flex-end', gap: 6, borderBottom: '1px solid rgba(60,60,67,.22)' }}>
        {keys.map((k, i) => { const mk = markOf.get(k), on = k === sel; return (
          <button key={k} onClick={() => setSel(k)} aria-pressed={on} aria-label={`${counts[i]} in ${name(k)}`}
            style={{ flex: 1, height: '100%', padding: 0, border: 'none', background: 'transparent', cursor: 'pointer', display: 'flex', flexDirection: 'column', justifyContent: 'flex-end', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 18, height: 18, borderRadius: 9, background: 'var(--ink)', color: '#FFFFFF', fontSize: 10.5, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: mk ? 1 : 0, flex: 'none' }}>{mk ?? ''}</span>
            <span style={{ display: 'block', width: '100%', height: `${Math.max(1.5, counts[i] / max * 82)}%`, background: on ? 'var(--blue)' : 'var(--blue-mid)', borderRadius: '5px 5px 1px 1px', transition: 'background-color .25s' }} />
          </button>); })}
      </div>
      <div style={{ display: 'flex', gap: 6, marginTop: 6 }}>
        {keys.map((k) => <span key={k} style={{ flex: 1, textAlign: 'center', fontSize: 12, fontWeight: k === sel ? 700 : 500, color: k === sel ? 'var(--blue)' : '#48484A' }}>{MONTH[+k.slice(5) - 1][0]}</span>)}
      </div>

      <div key={sel} style={{ marginTop: 14, padding: '12px 14px', borderRadius: 16, background: 'var(--bg)', display: 'flex', flexDirection: 'column', gap: 8, animation: 'rowIn .35s var(--ease-row) both' }}>
        <span style={{ fontSize: 15, fontWeight: 650 }}>{name(sel)}{isNow ? ', so far' : ''}</span>
        {m && n > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
            <Fact v={`${m.days_with_seizure}/${daysIn}`} k="days with one" />
            <Fact v={String(m.severe)} k="severe" />
            <Fact v={m.median_duration_s != null ? `${Math.round(m.median_duration_s)}s` : '—'} k="median length" />
          </div>
        ) : (
          <span style={{ fontSize: 14, color: 'var(--ink-3)' }}>No seizures logged{isNow ? ' yet' : ''} this month. Days without an entry aren’t counted as seizure-free.</span>
        )}
        {compare && n > 0 && <span style={{ fontSize: 13.5, color: 'var(--ink-2)' }}>{compare}.</span>}
        {changes.map((c) => (
          <span key={c.date + c.drug + c.action} style={{ fontSize: 13.5, lineHeight: 1.35 }}>
            <b>{+c.date.slice(8)} {MON[+c.date.slice(5, 7) - 1]}</b> · {c.drug.toLowerCase()} {ACTION[c.action] ?? c.action}. <span style={{ color: 'var(--ink-3)' }}>{sentence(c)}</span>
          </span>
        ))}
      </div>

      {shown.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 9, marginTop: 14, fontSize: 14, lineHeight: 1.35 }}>
          {shown.map((c, i) => (
            <button key={c.date + c.drug} onClick={() => setSel(c.date.slice(0, 7))} style={{ display: 'flex', gap: 10, alignItems: 'flex-start', border: 'none', background: 'transparent', padding: 0, textAlign: 'left', fontSize: 14, cursor: 'pointer' }}>
              <span style={{ flex: 'none', width: 18, height: 18, borderRadius: 9, background: 'var(--ink)', color: '#FFFFFF', fontSize: 10.5, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{i + 1}</span>
              <span><b>{name(c.date.slice(0, 7))}</b> · {c.drug.toLowerCase()} {ACTION[c.action] ?? c.action}. <span style={{ color: 'var(--ink-3)' }}>{sentence(c)}</span></span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

const Fact = ({ v, k }: { v: string; k: string }) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}><span style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>{v}</span><span style={{ fontSize: 12, color: 'var(--ink-3)' }}>{k}</span></div>
);

function Triggers({ triggers }: { triggers: TriggerTest[] }) {
  const sub = (t: TriggerTest) => {
    const notes = t.method.startsWith('notes only');
    const units = `${t.exposure_units} ${notes ? (t.exposure_units === 1 ? 'note' : 'notes') : 'days'}`;
    const r = t.ratio != null ? `${t.ratio.toFixed(1)}×` : null;
    if (t.rung === 'watching') return notes ? `${units} so far` : `${t.exposure_units} of 10 days logged`;
    return [r, `${units}${t.rung === 'emerging' ? ' so far' : ''}`].filter(Boolean).join(' · ');
  };
  return (
    <div className="card" style={{ margin: '0 16px 12px', padding: '16px 18px 6px' }}>
      <Head title="Triggers" right={`${triggers.length} tested`} />
      <div style={{ display: 'flex', flexDirection: 'column', marginTop: 8 }}>
        {triggers.length === 0 && <div className="hair-top muted" style={{ padding: '12px 0', fontSize: 14 }}>Nothing tested yet.</div>}
        {triggers.map((t) => (
          <div key={t.trigger_id} className="hair-top" style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '12px 0' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1, minWidth: 0 }}><span style={{ fontSize: 16, fontWeight: 600 }}>{t.trigger.charAt(0).toUpperCase() + t.trigger.slice(1)}</span><span style={{ fontSize: 13, color: 'var(--ink-3)' }}>{sub(t)}</span></div>
            <span className="rung" style={{ background: RUNG_COLORS[t.rung][0], color: RUNG_COLORS[t.rung][1] }}>{RUNG_LABEL[t.rung]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
