// Home fits one 390×844 viewport with no scrolling: header, risk card (flex: 1), Today card, Seizure bar, 12px gaps.
import { useEffect } from 'react';
import type { RiskNow, SeizureEvent } from '@seizure/contracts';
import { herOf, useStore } from '@/state/store';
import { clamp, daysAgo, headerDate, hhmm, minsOfDay } from '@/ui/format';

type Tier = 'low' | 'medium' | 'high' | 'overnight';
const ORDER: Tier[] = ['low', 'medium', 'high'];
const ALL: Tier[] = ['low', 'medium', 'high', 'overnight'];
const LABEL: Record<Tier, string> = { low: 'Low', medium: 'Medium', high: 'High', overnight: 'No data' };
const REASON_KEY: Record<string, string> = {
  hour_band: 'Time of day', today_count: 'Today', recent_gap: 'Last one', week_vs_baseline: 'This week',
  dose_overdue: 'Medication', dose_skipped: 'Medication', feeling_off: 'Warning signs', stress: 'Stress', short_sleep: 'Sleep',
};

export function Home() {
  const { profile, risk, today, year, loadHome, go, open, startTimer, screen } = useStore();
  useEffect(() => { void loadHome(); const id = setInterval(() => void loadHome(), 60_000); return () => clearInterval(id); }, [loadHome]);
  const name = profile?.display_name || (profile?.role === 'self' ? 'My diary' : 'Her diary');
  const pushed = screen === 'trends' || screen === 'account';
  return (
    <div className="screen" style={{ padding: 'var(--safe-top) 0 var(--safe-bottom)', display: 'flex', flexDirection: 'column', gap: 12, transform: pushed ? 'translateX(-28%)' : 'none' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', padding: '6px 20px 0', flex: 'none' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2, minWidth: 0 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-3)', letterSpacing: '.01em' }}>{headerDate()}</span>
          <span style={{ fontSize: 34, fontWeight: 700, letterSpacing: '-0.025em', lineHeight: 1.1 }}>{name}</span>
        </div>
        <button className="press" onClick={() => go('account')} aria-label="Account and settings" style={{ width: 44, height: 44, borderRadius: 22, border: 'none', background: 'var(--avatar)', fontSize: 17, fontWeight: 600, color: 'var(--ink-2)', flex: 'none' }}>
          {(profile?.display_name || 'H').trim().charAt(0).toUpperCase()}
        </button>
      </div>
      <RiskCard risk={risk} her={herOf(profile)} />
      <TodayCard today={today} year={year} onTrends={() => go('trends')} onOpen={(id) => open({ kind: 'detail', id })} sleepEnd={profile?.sleep_window?.end} />
      <div className="dock" style={{ margin: '0 14px', flex: 'none', opacity: screen === 'home' ? 1 : 0, pointerEvents: screen === 'home' ? 'auto' : 'none', transition: 'opacity .25s' }}>
        <button className="dock-btn press" onClick={startTimer}><PulseDot /><span>Seizure</span></button>
      </div>
    </div>
  );
}

function PulseDot() {
  return (
    <span style={{ position: 'relative', width: 12, height: 12, display: 'inline-block', flex: 'none' }}>
      <span style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: '#FFFFFF', animation: 'halo 2s ease-out infinite' }} />
      <span style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: '#FFFFFF' }} />
    </span>
  );
}

function RiskCard({ risk, her }: { risk: RiskNow | null; her: string }) {
  const tier: Tier = !risk ? 'overnight' : risk.overnight_no_data ? 'overnight' : risk.tier;
  const night = tier === 'overnight';
  const tIdx = ORDER.indexOf(tier);
  const reasons = night || !risk ? [] : risk.reasons.slice(0, 3);
  const line = !risk ? 'Loading…' : night ? `No score while ${her === 'her' ? 'she sleeps' : 'you sleep'}` : risk.learning_mode ? `Learning ${her} pattern` : 'for the next few hours';
  return (
    <div className="card" style={{ margin: '0 16px', flex: 1, minHeight: 0, padding: '16px 18px 12px', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 15, fontWeight: 600, color: `var(--${tier}-text, var(--overnight))`, transition: 'color .6s' }}>
          <span style={{ width: 9, height: 9, borderRadius: 5, background: `var(--${tier})`, transition: 'background-color .6s' }} />Seizure risk
        </span>
        <span style={{ fontSize: 14, color: 'var(--ink-3)' }}>{night ? 'While asleep' : 'Next few hours'}</span>
      </div>
      <div style={{ flex: 1, minHeight: 150, position: 'relative' }}>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', paddingBottom: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 24 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, width: 200 }}>
              <div style={{ position: 'relative', height: 60 }}>
                {ALL.map((w, i) => (
                  <span key={w} style={{ position: 'absolute', left: 0, top: 0, fontSize: 56, fontWeight: 750, letterSpacing: '-0.04em', lineHeight: '60px', paddingRight: 4, background: `var(--grad-${w})`, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent', opacity: w === tier ? 1 : 0, transform: `translateY(${w === tier ? 0 : i < ALL.indexOf(tier) ? -18 : 18}px)`, transition: 'opacity .45s ease, transform .7s cubic-bezier(.2,.9,.2,1)' }}>{LABEL[w]}</span>
                ))}
              </div>
              <span style={{ fontSize: 15, color: 'var(--ink-2)' }}>{line}</span>
            </div>
            <div role="img" aria-label={night ? 'No risk level overnight' : `${LABEL[tier]} risk, level ${tIdx + 1} of 3`} style={{ flex: 'none', display: 'flex', flexDirection: 'column-reverse', alignItems: 'flex-start', gap: 6, marginBottom: 22 }}>
              {[0, 1, 2].map((i) => <span key={i} style={{ height: 12, width: 26 + i * 12, borderRadius: 6, background: !night && i <= tIdx ? `var(--${tier})` : 'var(--meter-off)', transition: `background-color .6s ease ${i * 80}ms` }} />)}
            </div>
          </div>
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {reasons.map((r, i) => (
          <div key={r.factor + i} className="hair-top" style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: 12, padding: '11px 0', animation: `rowIn .45s var(--ease-row) ${i * 90}ms both` }}>
            <span style={{ fontSize: 14, color: 'var(--ink-3)', flex: 'none' }}>{REASON_KEY[r.factor] ?? r.factor}</span>
            <span style={{ fontSize: 15, fontWeight: 600, textAlign: 'right' }}>{r.text}</span>
          </div>
        ))}
        {night && <div className="hair-top" style={{ padding: '10px 0', fontSize: 15, lineHeight: 1.4, color: 'var(--ink-2)' }}>Nothing is logged while {her === 'her' ? 'she sleeps' : 'you sleep'}, so there’s no score until morning.</div>}
        <div className="hair-top" style={{ marginTop: 'auto', paddingTop: 6, fontSize: 9.5, lineHeight: 1.3, color: 'var(--ink-3)' }}>
          A pattern from {her} own diary, not a prediction. Low never means safe. Research prototype.
        </div>
      </div>
    </div>
  );
}

function TodayCard({ today, year, onTrends, onOpen, sleepEnd }: { today: SeizureEvent[]; year: SeizureEvent[]; onTrends: () => void; onOpen: (id: string) => void; sleepEnd?: string }) {
  const sorted = [...today].sort((a, b) => minsOfDay(a.start_time) - minsOfDay(b.start_time));
  // Pills sit at their time of day and stack into 2 lanes when within 3.6 h; a third collision merges into "+N".
  const pills: { m: number; lv: number; ids: string[]; t: string }[] = [];
  sorted.forEach((s) => {
    const m = minsOfDay(s.start_time); let lv = 0;
    while (lv < 2 && pills.some((p) => p.lv === lv && Math.abs(p.m - m) < 216)) lv++;
    if (lv < 2) pills.push({ m, lv, ids: [s.id!], t: s.start_time });
    else { const near = pills.filter((p) => p.lv === 1).sort((a, b) => Math.abs(a.m - m) - Math.abs(b.m - m))[0]; near.ids.push(s.id!); near.t = s.start_time; }
  });
  const maxLv = Math.max(0, ...pills.map((p) => p.lv));
  const nowLeft = `${(minsOfDay(new Date()) / 1440 * 100).toFixed(2)}%`;
  const wakeH = parseInt((sleepEnd ?? '07:00').split(':')[0], 10);
  const since30 = daysAgo(30).getTime();
  const convulsive12m = year.filter((e) => e.type === 'convulsive').length;
  const night30 = year.filter((e) => new Date(e.start_time).getTime() >= since30 && (e.asleep_at_onset || new Date(e.start_time).getHours() < wakeH)).length;
  return (
    <div className="card press" onClick={onTrends} style={{ margin: '0 16px', flex: 'none', padding: '16px 18px 14px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span className="card-title"><span className="dot9" />Today</span>
        <span style={{ fontSize: 14, color: 'var(--ink-3)', display: 'flex', alignItems: 'center', gap: 5 }}>Trends<span style={{ fontSize: 18, lineHeight: '14px', color: 'var(--chev)' }}>›</span></span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: 4 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}><span style={{ fontSize: 32, fontWeight: 700, letterSpacing: '-0.03em' }}>{today.length}</span><span className="big-unit">{today.length === 1 ? 'seizure' : 'seizures'}</span></div>
        {today.length > 0 && <span style={{ fontSize: 13, color: 'var(--ink-3)' }}>Tap a time for details</span>}
      </div>
      <div style={{ position: 'relative', height: 78 + maxLv * 34, marginTop: 6, transition: 'height .4s' }}>
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: 24, height: 6, borderRadius: 3, background: 'var(--track)' }} />
        <div style={{ position: 'absolute', left: 0, width: nowLeft, bottom: 24, height: 6, borderRadius: 3, background: 'var(--blue-track)' }} />
        <div style={{ position: 'absolute', left: nowLeft, bottom: 18, width: 3, height: 18, marginLeft: -1.5, borderRadius: 2, background: 'var(--ink)' }} />
        {pills.map((p) => (
          <button key={p.ids.join()} onClick={(e) => { e.stopPropagation(); onOpen(p.ids[p.ids.length - 1]); }}
            style={{ position: 'absolute', left: `${clamp(p.m / 1440 * 100, 8, 92).toFixed(2)}%`, bottom: 42 + p.lv * 34, transform: 'translateX(-50%)', height: 30, padding: '0 11px', borderRadius: 15, border: '2px solid #FFFFFF', background: 'var(--blue)', color: '#FFFFFF', fontSize: 13.5, fontWeight: 700, fontVariantNumeric: 'tabular-nums', cursor: 'pointer', boxShadow: '0 3px 10px oklch(0.53 0.2 257 / .35)', transition: 'bottom .4s cubic-bezier(.2,.9,.2,1)', minWidth: 44 }}>
            <span style={{ display: 'block', animation: 'pop .55s var(--ease-pop) .2s both' }}>{hhmm(p.t)}{p.ids.length > 1 ? ` +${p.ids.length - 1}` : ''}</span>
          </button>
        ))}
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 16, fontSize: 12.5, fontWeight: 600, color: 'var(--ink-2)' }}>
          <span style={{ position: 'absolute', left: 0 }}>00:00</span>
          {[25, 50, 75].map((p, i) => <span key={p} style={{ position: 'absolute', left: `${p}%`, transform: 'translateX(-50%)' }}>{['06:00', '12:00', '18:00'][i]}</span>)}
          <span style={{ position: 'absolute', right: 0 }}>24:00</span>
        </div>
      </div>
      <div className="hair-top" style={{ display: 'flex', gap: 18, marginTop: 10, paddingTop: 10, fontSize: 13, color: 'var(--ink-3)' }}>
        <span><b style={{ color: 'var(--ink)', fontSize: 15 }}>{convulsive12m}</b> convulsive · 12 months</span>
        <span><b style={{ color: 'var(--ink)', fontSize: 15 }}>{night30}</b> at night · 30 days</span>
      </div>
    </div>
  );
}
