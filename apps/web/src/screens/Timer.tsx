// The blue timer. The Seizure bar has already written the tap event; this screen only times it.
// From 5:00 (the convulsive rule) the emergency card appears; the full plan is one tap from it.
import { useEffect, useState } from 'react';
import { useStore } from '@/state/store';
import { Icon, IC } from '@/ui/icons';
import { clamp, durTxt, hhmm, mmss } from '@/ui/format';

export function BlueFill() {
  const screen = useStore((s) => s.screen);
  const on = screen === 'timer' || screen === 'talk';
  return <div style={{ position: 'absolute', left: '50%', bottom: 28, width: 64, height: 64, marginLeft: -32, zIndex: 20, borderRadius: '50%', background: 'var(--blue)', pointerEvents: 'none', opacity: on ? 1 : 0, transform: on ? 'scale(30)' : 'scale(1)', transition: `transform .7s var(--ease-screen), opacity .3s ${on ? '0s' : '.6s'}` }} />;
}

export function Timer() {
  const { screen, timer, stopTimer, discardTimer, finishTimer, go, open, profile } = useStore();
  const [now, setNow] = useState(Date.now());
  const visible = screen === 'timer';
  const running = !!timer && !timer.stoppedAt;
  useEffect(() => { if (!running) return; const id = setInterval(() => setNow(Date.now()), 250); return () => clearInterval(id); }, [running]);
  if (!timer) return null;
  const el = Math.max(0, ((timer.stoppedAt ?? now) - timer.t0) / 1000);
  const started = hhmm(new Date(timer.t0));
  const limit = (profile?.rescue_plan?.emergency_minutes_convulsive ?? 5) * 60;
  const call = profile?.rescue_plan?.call?.[0] ?? '999';
  return (
    <div style={{ position: 'absolute', inset: 0, zIndex: 21, padding: 'calc(var(--safe-top) + 13px) 22px var(--safe-bottom)', display: 'flex', flexDirection: 'column', color: '#FFFFFF', opacity: visible ? 1 : 0, pointerEvents: visible ? 'auto' : 'none', transition: `opacity .35s ${visible ? '.3s' : '0s'}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', height: 36 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, fontSize: 16, fontWeight: 600 }}>
          {running
            ? <><span style={{ width: 10, height: 10, borderRadius: 5, background: '#FFFFFF', display: 'inline-block', animation: 'blink 1.3s ease-in-out infinite' }} /><span>Timing</span></>
            : <><span style={{ width: 20, height: 20, borderRadius: 10, background: '#FFFFFF', color: 'var(--blue)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon d={IC.check} size={12} stroke={3} /></span><span>Stopped</span></>}
        </div>
        <button onClick={() => void discardTimer()} style={{ height: 36, padding: '0 4px', border: 'none', background: 'transparent', color: 'rgba(255,255,255,.8)', fontSize: 15, fontWeight: 500, cursor: 'pointer' }}>Discard</button>
      </div>
      <div style={{ fontSize: 112, fontWeight: 600, letterSpacing: '-0.05em', lineHeight: 1, marginTop: 64, fontVariantNumeric: 'tabular-nums', transform: `scale(${running ? 1 : 0.86})`, transformOrigin: 'left center', transition: 'transform .5s var(--ease-pop)' }}>{mmss(el)}</div>
      <div style={{ marginTop: 12, fontSize: 17, color: 'rgba(255,255,255,.82)' }}>{running ? `Started ${started}` : `Lasted ${durTxt(el)} · started ${started}`}</div>
      <div style={{ display: 'flex', gap: 6, marginTop: 30 }}>
        {[0, 1, 2, 3, 4].map((i) => (
          <div key={i} style={{ flex: 1, height: 8, borderRadius: 4, background: 'rgba(255,255,255,.2)', overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${(clamp(el / 60 - i, 0, 1) * 100).toFixed(1)}%`, background: '#FFFFFF', borderRadius: 4, transition: 'width .25s linear' }} />
          </div>
        ))}
      </div>
      <div style={{ marginTop: 9, fontSize: 13, color: 'rgba(255,255,255,.75)' }}>One bar per minute</div>
      {el >= limit && (
        <div style={{ marginTop: 22, background: '#FFFFFF', color: 'var(--ink)', borderRadius: 22, padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 10, animation: 'rowIn .45s var(--ease-row) both' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ flex: 'none', width: 36, height: 36, borderRadius: 11, background: 'var(--emergency-bg)', color: 'var(--high-text)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><Icon d={IC.cross} /></span>
            <span style={{ fontSize: 15, lineHeight: 1.35 }}><b>Past {limit / 60} minutes.</b> If it is convulsive, call {call} now. Recovery position, nothing in the mouth.</span>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <a href={`tel:${call}`} style={{ flex: 1, height: 48, borderRadius: 24, background: 'var(--high-text)', color: '#FFFFFF', fontSize: 17, fontWeight: 650, display: 'flex', alignItems: 'center', justifyContent: 'center', textDecoration: 'none' }}>Call {call}</a>
            <button onClick={() => open({ kind: 'emergency' })} style={{ flex: 'none', height: 48, padding: '0 16px', borderRadius: 24, border: 'none', background: 'var(--bg)', fontSize: 15, fontWeight: 600, cursor: 'pointer' }}>Plan</button>
          </div>
        </div>
      )}
      <div style={{ flex: 1 }} />
      {running ? (
        <button className="press" onClick={() => void stopTimer()} style={{ height: 72, borderRadius: 36, border: 'none', background: '#FFFFFF', color: 'var(--ink)', fontSize: 20, fontWeight: 650, animation: 'rowIn .4s var(--ease-row) both' }}>It’s over</button>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, animation: 'rowIn .45s var(--ease-row) both' }}>
          <button className="press" onClick={() => go('talk')} style={{ height: 72, borderRadius: 36, border: 'none', background: '#FFFFFF', color: 'var(--ink)', fontSize: 20, fontWeight: 650, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 11 }}>
            <span style={{ width: 11, height: 11, borderRadius: 6, background: 'var(--blue)' }} />Tell me about it
          </button>
          <button className="press" onClick={() => void finishTimer()} style={{ height: 60, borderRadius: 30, border: 'none', background: 'rgba(255,255,255,.18)', color: '#FFFFFF', fontSize: 18, fontWeight: 600 }}>Done</button>
        </div>
      )}
    </div>
  );
}
