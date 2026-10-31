// The quick path: one tap timestamps a seizure and starts a timer; a second tap stops it and offers the voice debrief.
// Escalation thresholds come from the profile's rescue plan (5 min convulsive / 10 min other by default).
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '@/state/store';

export function TapButton() {
  const { timer, tap, stopTimer, profile } = useStore();
  const [now, setNow] = useState(Date.now());
  const nav = useNavigate();
  useEffect(() => { if (!timer.startedAt) return; const id = setInterval(() => setNow(Date.now()), 500); return () => clearInterval(id); }, [timer.startedAt]);

  if (!timer.startedAt) {
    return <button className="btn primary big" onClick={() => void tap()}>Just had one — start timer</button>;
  }
  const secs = Math.floor((now - timer.startedAt) / 1000);
  const limitOther = (profile?.rescue_plan.emergency_minutes_other ?? 10) * 60;
  const limitConv = (profile?.rescue_plan.emergency_minutes_convulsive ?? 5) * 60;
  const warn = secs >= limitConv;
  const mm = String(Math.floor(secs / 60)).padStart(2, '0'), ss = String(secs % 60).padStart(2, '0');
  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div className={`timer ${warn ? 'warn' : ''}`}>{mm}:{ss}</div>
      {warn && <div className="error">Past {limitConv / 60} minutes. If convulsive, follow the emergency plan now. {secs >= limitOther ? `Past ${limitOther / 60} minutes for any type.` : ''}</div>}
      <div className="row">
        <button className="btn primary grow" onClick={async () => { await stopTimer(); nav('/log'); }}>It's over — tell me about it</button>
        <button className="btn ghost" onClick={() => void stopTimer()}>Stop</button>
      </div>
      {warn && <button className="btn danger" onClick={() => nav('/emergency')}>Emergency plan</button>}
    </div>
  );
}
