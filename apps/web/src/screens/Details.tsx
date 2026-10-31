// Seizure details as a "Lead-up" timeline: the hours before the seizure, earliest first, each factor with its rung
// from the trigger lab. Same time windows the engine tests, so what carers add is already in the shape it needs.
import { useEffect, useState } from 'react';
import type { SeizureEvent } from '@seizure/contracts';
import { herOf, useStore } from '@/state/store';
import { CAT_KEYS, entryFor, factorLabels, statFor, toggleFactor } from '@/ui/catalogue';
import { Icon, IC } from '@/ui/icons';
import { durTxt, hhmm, minsOfDay, parseDur } from '@/ui/format';

const SOURCE: Record<string, string> = { tap: 'By tap', voice: 'By tap + voice', import: 'Imported', manual: 'Typed in' };

export function DetailsSheet({ id, onClose }: { id: string; onClose: () => void }) {
  const { today, year, triggers, profile, patchEvent, deleteEvent, loadTriggers } = useStore();
  const ev = today.find((e) => e.id === id) ?? year.find((e) => e.id === id);
  useEffect(() => { if (!triggers.length) void loadTriggers(); }, [triggers.length, loadTriggers]);
  if (!ev) return <div style={{ padding: 20 }} className="muted">This seizure is no longer in the diary.</div>;
  return <Body key={ev.id} ev={ev} her={herOf(profile)} onClose={onClose} sameDay={today.some((e) => e.id === ev.id) ? today : []}
    stat={(l) => statFor(l, triggers, herOf(profile))} patch={(p) => void patchEvent(ev.id!, p)} del={() => void deleteEvent(ev.id!)} />;
}

function Body({ ev, her, onClose, sameDay, stat, patch, del }: {
  ev: SeizureEvent; her: string; onClose: () => void; sameDay: SeizureEvent[];
  stat: (label: string) => { text: string; color: string }; patch: (p: Partial<SeizureEvent>) => void; del: () => void;
}) {
  const [time, setTime] = useState(hhmm(ev.start_time));
  const [dur, setDur] = useState(durTxt(ev.duration_s));
  const [what, setWhat] = useState(ev.original_label ?? '');
  const [recovery, setRecovery] = useState(ev.recovery_text ?? '');
  const [notes, setNotes] = useState(ev.notes ?? '');
  const [draft, setDraft] = useState('');
  const aware = ev.awareness === 'kept';
  const labels = factorLabels(ev);
  const tl = labels.map((l) => ({ label: l, ...entryFor(l), stat: stat(l) })).sort((a, b) => b.rank - a.rank);
  const isToday = new Date(ev.start_time).toDateString() === new Date().toDateString();
  const day = isToday ? 'Today' : new Date(ev.start_time).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });

  const commitTime = () => {
    const m = /^(\d{1,2}):(\d{2})$/.exec(time.trim());
    if (!m || +m[1] > 23 || +m[2] > 59) { setTime(hhmm(ev.start_time)); return; }
    const d = new Date(ev.start_time); d.setHours(+m[1], +m[2], 0, 0);
    if (d.toISOString() !== new Date(ev.start_time).toISOString()) patch({ start_time: d.toISOString() });
  };
  const commitDur = () => { const s = parseDur(dur); if (s == null) { setDur(durTxt(ev.duration_s)); return; } setDur(durTxt(s)); if (s !== ev.duration_s) patch({ duration_s: s, duration_estimated: false }); };
  const toggle = (l: string) => patch(toggleFactor(ev, l));
  const addOwn = () => { const v = draft.trim(); if (!v) return; if (!labels.includes(v)) toggle(v); setDraft(''); };

  return (
    <>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 16px 12px 20px', flex: 'none' }}>
        <span className="card-title"><span className="dot9" />Seizure · {day}</span>
        <button className="pill-btn" onClick={onClose}>Done</button>
      </div>
      <div className="scr" style={{ flex: 1, overflowY: 'auto', padding: '0 16px 30px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div className="card" style={{ padding: '14px 18px 12px', display: 'flex', flexDirection: 'column', gap: 12, flex: 'none' }}>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 16 }}>
            <label style={{ display: 'flex', flexDirection: 'column' }}><span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-3)' }}>Started</span>
              <input value={time} onChange={(e) => setTime(e.target.value)} onBlur={commitTime} onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()} inputMode="numeric" aria-label="Start time"
                style={{ width: 118, border: 'none', background: 'transparent', fontSize: 40, fontWeight: 700, letterSpacing: '-0.03em', padding: 0, fontVariantNumeric: 'tabular-nums' }} /></label>
            <label style={{ display: 'flex', flexDirection: 'column' }}><span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-3)' }}>Lasted</span>
              <input value={dur} onChange={(e) => setDur(e.target.value)} onBlur={commitDur} onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()} placeholder="—" aria-label="How long it lasted"
                style={{ width: 100, border: 'none', background: 'transparent', fontSize: 24, fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--ink-2)', padding: '0 0 5px' }} /></label>
            <button onClick={() => patch({ awareness: aware ? 'impaired' : 'kept' })} style={{ marginLeft: 'auto', marginBottom: 6, height: 32, padding: '0 12px', borderRadius: 16, border: 'none', background: aware ? 'var(--blue-soft)' : 'var(--ink)', color: aware ? 'var(--blue)' : '#FFFFFF', fontSize: 13.5, fontWeight: 650, cursor: 'pointer', transition: 'background .3s var(--ease-pop)' }}>{aware ? 'Aware' : 'Not aware'}</button>
          </div>
          <div style={{ position: 'relative', height: 34 }}>
            <div style={{ position: 'absolute', left: 0, right: 0, top: 9, height: 4, borderRadius: 2, background: 'var(--track)' }} />
            {(sameDay.length ? sameDay : [ev]).map((s) => { const me = s.id === ev.id, sz = me ? 18 : 10; return (
              <span key={s.id} style={{ position: 'absolute', top: 11 - sz / 2, left: `${minsOfDay(s.start_time) / 1440 * 100}%`, marginLeft: -sz / 2, width: sz, height: sz, borderRadius: '50%', background: me ? 'var(--blue)' : 'var(--blue-mid)', border: '2px solid #FFFFFF' }} />); })}
            <span style={{ position: 'absolute', left: 0, bottom: 0, fontSize: 11.5, fontWeight: 600, color: 'var(--ink-3)' }}>00:00</span>
            <span style={{ position: 'absolute', left: '50%', bottom: 0, transform: 'translateX(-50%)', fontSize: 11.5, fontWeight: 600, color: 'var(--ink-3)' }}>12:00</span>
            <span style={{ position: 'absolute', right: 0, bottom: 0, fontSize: 11.5, fontWeight: 600, color: 'var(--ink-3)' }}>24:00</span>
          </div>
        </div>

        <div className="card" style={{ padding: '14px 18px 6px', flex: 'none' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}><span style={{ fontSize: 15, fontWeight: 600 }}>Leading up to it</span><span style={{ fontSize: 13, color: 'var(--ink-3)' }}>{labels.length ? `${labels.length} added` : ''}</span></div>
          <span style={{ display: 'block', padding: '2px 0 6px', fontSize: 13, color: 'var(--ink-3)' }}>In order, as best you remember. Rough is fine.</span>
          <div style={{ position: 'relative' }}>
            <div style={{ position: 'absolute', left: 92, top: 20, bottom: 24, width: 2, marginLeft: -1, background: 'var(--fill-2)' }} />
            {tl.map((r) => (
              <div key={r.label} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 0', position: 'relative', animation: 'rowIn .45s var(--ease-row) both' }}>
                <span style={{ width: 66, flex: 'none', textAlign: 'right', fontSize: 12.5, fontWeight: 600, color: 'var(--ink-3)', lineHeight: 1.2 }}>{r.when}</span>
                <span style={{ flex: 'none', width: 34, height: 34, borderRadius: 17, background: '#FFFFFF', border: '2px solid oklch(0.86 0.06 257)', color: 'var(--blue)', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', zIndex: 1 }}><Icon d={r.icon} size={17} /></span>
                <span style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 2, paddingLeft: 2 }}><span style={{ fontSize: 15, fontWeight: 650 }}>{r.label}</span><span style={{ fontSize: 12, fontWeight: 600, color: r.stat.color }}>{r.stat.text}</span></span>
                <button onClick={() => toggle(r.label)} aria-label={`Remove ${r.label}`} style={{ flex: 'none', width: 30, height: 30, borderRadius: 15, border: 'none', background: 'var(--bg)', color: 'var(--ink-3)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}><Icon d={IC.x} size={12} stroke={2.6} /></button>
              </div>
            ))}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 0 12px' }}>
              <span style={{ width: 66, flex: 'none', textAlign: 'right', fontSize: 13, fontWeight: 700, color: 'var(--blue)' }}>{hhmm(ev.start_time)}</span>
              <span style={{ flex: 'none', width: 34, height: 34, borderRadius: 17, background: 'var(--blue)', boxShadow: '0 0 0 6px oklch(0.6 0.2 257 / .15)', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative', zIndex: 1 }}><span style={{ width: 10, height: 10, borderRadius: 5, background: '#FFFFFF' }} /></span>
              <span style={{ display: 'flex', flexDirection: 'column', gap: 2, paddingLeft: 2 }}><span style={{ fontSize: 15, fontWeight: 700 }}>Seizure</span><span style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink-3)' }}>{[durTxt(ev.duration_s), aware ? 'Aware' : 'Not aware'].filter(Boolean).join(' · ')}</span></span>
            </div>
          </div>
        </div>

        <div className="card" style={{ padding: '14px 18px 16px', flex: 'none' }}>
          <span style={{ fontSize: 15, fontWeight: 600 }}>Add to the timeline</span>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
            {CAT_KEYS.filter((l) => !labels.includes(l)).map((l) => (
              <button key={l} className="add-chip press" onClick={() => toggle(l)}><span style={{ color: 'var(--blue)', display: 'flex' }}><Icon d={entryFor(l).icon} size={17} /></span>{l}</button>
            ))}
            <span className="own">
              <input value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addOwn()} placeholder="Your own" aria-label="Add your own trigger" />
              <button className="round-add" onClick={addOwn} aria-label="Add"><Icon d={IC.plus} size={13} stroke={2.6} /></button>
            </span>
          </div>
        </div>

        <div className="card" style={{ padding: '2px 18px', flex: 'none' }}>
          <Row k="What happened" v={what} set={setWhat} save={() => what !== (ev.original_label ?? '') && patch({ original_label: what || null })} ph="In your words" />
          <Row k="Recovery" v={recovery} set={setRecovery} save={() => recovery !== (ev.recovery_text ?? '') && patch({ recovery_text: recovery || null })} ph="e.g. sleepy for an hour" />
          <Row k="Notes" v={notes} set={setNotes} save={() => notes !== (ev.notes ?? '') && patch({ notes: notes || null })} ph="Anything else" />
          <div className="kv"><span className="k">Logged</span><span style={{ fontSize: 15, color: 'var(--ink-3)' }}>{ev.synthetic ? 'Demo data' : SOURCE[ev.source] ?? ev.source}</span></div>
        </div>
        <button onClick={() => { if (confirm(`Delete this seizure from ${her} diary?`)) del(); }} style={{ height: 44, border: 'none', background: 'transparent', color: 'var(--danger)', fontSize: 15, fontWeight: 500, cursor: 'pointer', flex: 'none' }}>Delete this seizure</button>
      </div>
    </>
  );
}

function Row({ k, v, set, save, ph }: { k: string; v: string; set: (s: string) => void; save: () => void; ph: string }) {
  return (
    <div className="kv"><span className="k">{k}</span>
      <input value={v} onChange={(e) => set(e.target.value)} onBlur={save} onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()} placeholder={ph} aria-label={k} />
    </div>
  );
}
