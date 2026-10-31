// "Blue room": after "Tell me about it" the screen stays in the timer's blue. The Live agent calls note() as it hears
// facts and they appear as chips; nothing is saved until "Save to diary", which runs the extractor over the transcript,
// applies the chips the carer kept, and updates the event the Seizure bar already wrote.
import { useEffect, useRef, useState } from 'react';
import type { SeizureEvent } from '@seizure/contracts';
import { api } from '@/api/client';
import { LiveSession, type LiveEvent } from '@/live/liveClient';
import { useStore } from '@/state/store';
import { CAT, CAT_KEYS, tagLabel } from '@/ui/catalogue';
import { Icon, IC } from '@/ui/icons';
import { durTxt, hhmm } from '@/ui/format';

type Kind = 'what_happened' | 'awareness' | 'before' | 'medication' | 'new_factor';
type Chip = { id: string; kind: Kind; label: string; status: 'on' | 'pending' | 'yes' | 'no' };
type Line = { role: 'user' | 'model'; text: string };
const OPENER = 'I’m listening. What happened?';

/** Map whatever the agent called it onto the catalogue name when there is one ("Hot shower just before" → "Hot shower"). */
function canonical(label: string): string {
  const l = label.toLowerCase();
  const hit = CAT_KEYS.find((k) => l.includes(k.toLowerCase())) ?? (/(shower|bath)/.test(l) ? 'Hot shower' : /(lunch|meal|breakfast|eat)/.test(l) ? 'Skipped meal' : undefined);
  return hit ?? label.charAt(0).toUpperCase() + label.slice(1);
}
const iconFor = (label: string) => CAT[canonical(label)]?.icon ?? IC.dot;

export function Talk() {
  const { screen, timer, go, timedEventId, finishTimer, loadTriggers } = useStore();
  const visible = screen === 'talk';
  const session = useRef<LiveSession | null>(null);
  const startedFor = useRef<number | null>(null);
  const removed = useRef<string[]>([]);
  const [lines, setLines] = useState<Line[]>([]);
  const [chips, setChips] = useState<Chip[]>([]);
  const [speaking, setSpeaking] = useState(false);
  const [muted, setMuted] = useState(false);
  const [mock, setMock] = useState(false);
  const [typing, setTyping] = useState(false);
  const [typed, setTyped] = useState('');
  const [status, setStatus] = useState('');
  const [saving, setSaving] = useState(false);

  const onEvent = (e: LiveEvent) => {
    if (e.type === 'user_text' || e.type === 'model_text') setLines((session.current?.transcript ?? []).map((l) => ({ ...l })));
    if (e.type === 'speaking') setSpeaking(e.on);
    if (e.type === 'mock') { setMock(true); setTyping(true); }
    if (e.type === 'error') setStatus(e.text);
    if (e.type === 'tool' && e.name === 'note') {
      const kind = String(e.args.kind ?? 'before') as Kind;
      const label = String(e.args.label ?? '').trim();
      if (!label || removed.current.includes(label.toLowerCase())) return;
      setChips((cs) => (cs.some((c) => c.label.toLowerCase() === label.toLowerCase()) ? cs
        : [...cs, { id: `${Date.now()}-${cs.length}`, kind, label, status: kind === 'new_factor' ? 'pending' : 'on' }]));
    }
  };

  // One Live session per timed seizure, opened the first time the room is shown (the tap is the mic gesture).
  useEffect(() => {
    if (!visible || !timer || startedFor.current === timer.t0) return;
    startedFor.current = timer.t0;
    removed.current = []; setLines([]); setChips([]); setMock(false); setTyping(false); setTyped(''); setStatus(''); setMuted(false);
    void (async () => {
      const id = await timedEventId();
      const s = new LiveSession(); s.onEvent = onEvent; session.current = s;
      try { await s.start(id ?? undefined); } catch (err) { setStatus(String(err)); setMock(true); setTyping(true); }
    })();
  }, [visible, timer]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!timer && session.current) { void session.current.stop(); session.current = null; startedFor.current = null; } }, [timer]);
  useEffect(() => { session.current?.setMuted(!visible || muted); }, [visible, muted]);
  useEffect(() => () => { void session.current?.stop(); }, []);

  if (!timer) return <div className="screen" style={{ zIndex: 30, background: 'var(--blue)', transform: 'translateX(100%)' }} />;
  const dur = Math.round(((timer.stoppedAt ?? Date.now()) - timer.t0) / 1000);
  const last = lines[lines.length - 1];
  const curWho = !last || last.role === 'model' ? 'ASSISTANT' : 'YOU';
  const words = (last?.text ?? OPENER).trim().split(/\s+/);
  const curText = (words.length > 26 ? '… ' : '') + words.slice(-26).join(' ');
  const state = mock ? 'Type what happened' : saving ? 'All noted' : muted ? 'Paused' : speaking ? 'Speaking' : 'Listening';
  const seizChips = chips.filter((c) => c.kind === 'what_happened' || c.kind === 'awareness');
  const beforeChips = chips.filter((c) => c.kind === 'before' || c.kind === 'medication' || (c.kind === 'new_factor' && c.status === 'yes'));
  const pending = chips.filter((c) => c.kind === 'new_factor' && c.status === 'pending');
  const total = seizChips.length + beforeChips.length;
  const remove = (c: Chip) => { removed.current.push(c.label.toLowerCase()); setChips((cs) => cs.filter((x) => x.id !== c.id)); };
  const decide = (c: Chip, s: 'yes' | 'no') => setChips((cs) => cs.map((x) => (x.id === c.id ? { ...x, status: s } : x)));

  const save = async () => {
    if (saving) return;
    setSaving(true);
    const s = session.current;
    const spoken = s && s.transcript.length ? s.transcriptText() : typed.trim() ? `Carer: ${typed.trim()}` : '';
    await s?.stop(); session.current = null;
    const id = await timedEventId();
    let patch: Partial<SeizureEvent> = { source: 'voice', still_going: false };
    if (spoken) {
      const context = `App: Seizure logged with the timer button, started ${new Date(timer.t0).toISOString()}, lasted ${dur} seconds (timed, exact).\nAssistant: ${OPENER}\n`;
      try {
        const b = await api.extract(context + spoken);
        const x = b.seizures[0];
        if (x) patch = { ...patch, type: x.type, severity: x.severity, awareness: x.awareness, warning_before: x.warning_before, warning_text: x.warning_text, rescue_med: x.rescue_med, asleep_at_onset: x.asleep_at_onset, injury: x.injury, confidence: x.confidence, notes: x.notes, context_tags: x.context_tags ?? [] };
        for (const d of b.doses) await api.addDose(d).catch(() => undefined);
      } catch (err) { setStatus(String(err)); }
    }
    // The chips are the record the carer saw: they say what happened and what came before. Removing a chip removes it.
    const what = chips.filter((c) => c.kind === 'what_happened').map((c) => c.label);
    if (what.length) patch.original_label = what.join(', ');
    const aw = chips.find((c) => c.kind === 'awareness');
    if (aw) patch.awareness = /lost|unconscious/i.test(aw.label) ? 'lost' : /not|unaware|couldn|impaired/i.test(aw.label) ? 'impaired' : 'kept';
    const tags = (patch.context_tags ?? []).filter((t) => !removed.current.includes(tagLabel(t).toLowerCase()));
    const factors: string[] = [];
    beforeChips.forEach((c) => {
      if (c.kind === 'medication') { if (/miss|not|skip|late|forgot/i.test(c.label) && !factors.includes('Missed dose')) factors.push('Missed dose'); return; }
      const name = canonical(c.label); const tag = CAT[name]?.tag;
      if (tag) { if (!tags.includes(tag)) tags.push(tag); } else if (!factors.includes(name)) factors.push(name);
    });
    patch.context_tags = tags; patch.factors = factors;
    if (id) await api.patchEvent(id, patch).catch((err) => setStatus(String(err)));
    for (const c of chips.filter((x) => x.kind === 'new_factor' && x.status === 'yes')) await api.addTrigger({ name: canonical(c.label), kind: 'exposure' }).catch(() => undefined);
    setSaving(false);
    await finishTimer(`Saved · ${hhmm(new Date(timer.t0))} · ${durTxt(dur)}`);
    void loadTriggers();
  };

  return (
    <div className="screen" style={{ zIndex: 30, background: 'var(--blue)', transform: visible ? 'none' : 'translateX(100%)', boxShadow: '-10px 0 30px rgba(0,0,0,.08)' }}>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 'var(--safe-top)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 20px 0 12px', zIndex: 3 }}>
        <button className="back" onClick={() => go('timer')} style={{ color: '#FFFFFF' }}><span>‹</span>Timer</button>
        <span style={{ fontSize: 14, color: 'rgba(255,255,255,.8)' }}>{hhmm(new Date(timer.t0))} · {durTxt(dur)}</span>
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 'calc(var(--safe-top) + 50px)', bottom: 0, display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 'none', minHeight: 230, maxHeight: 282, padding: '6px 26px 18px', display: 'flex', flexDirection: 'column', gap: 12, color: '#FFFFFF', overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, height: 44 }}><WhiteOrb active={!muted && !mock && !saving} talking={speaking} /><span style={{ fontSize: 15, fontWeight: 600, color: 'rgba(255,255,255,.88)' }}>{state}</span></div>
          <span style={{ fontSize: 12.5, fontWeight: 700, letterSpacing: '.07em', color: 'rgba(255,255,255,.7)' }}>{curWho}</span>
          <span key={lines.length} style={{ fontSize: 29, fontWeight: 650, letterSpacing: '-0.025em', lineHeight: 1.18, textWrap: 'balance' } as React.CSSProperties}>{curText}</span>
        </div>
        <div className="scr" style={{ flex: 1, minHeight: 0, background: '#FFFFFF', borderRadius: '30px 30px 0 0', padding: '10px 20px 124px', overflowY: 'auto', color: 'var(--ink)', boxShadow: '0 -10px 30px rgba(0,20,80,.18)', transform: visible ? 'none' : 'translateY(40%)', transition: 'transform .7s var(--ease-screen) .1s' }}>
          <div className="handle" style={{ paddingBottom: 8, paddingTop: 0 }}><span style={{ background: '#D1D1D6' }} /></div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}><span style={{ fontSize: 20, fontWeight: 700, letterSpacing: '-0.02em' }}>Picked up</span><span style={{ fontSize: 13, color: 'var(--ink-3)' }}>{total ? `${total} ${total === 1 ? 'thing' : 'things'}` : ''}</span></div>
          <Label>THE SEIZURE</Label>
          {seizChips.length === 0 && <Nothing />}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
            {seizChips.map((c) => <span key={c.id} className="chip">{c.label}<button className="chip-x" aria-label="Remove" onClick={() => remove(c)}><Icon d={IC.x} size={11} stroke={2.8} /></button></span>)}
          </div>
          <Label>BEFORE IT</Label>
          {beforeChips.length === 0 && <Nothing />}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
            {beforeChips.map((c) => (
              <span key={c.id} className="chip blue"><Icon d={c.kind === 'medication' ? IC.pill : iconFor(c.label)} size={15} stroke={2} />{c.label}
                <button className="chip-x" aria-label="Remove" onClick={() => (c.kind === 'new_factor' ? decide(c, 'no') : remove(c))}><Icon d={IC.x} size={11} stroke={2.8} /></button></span>
            ))}
          </div>
          {pending.map((c) => (
            <div key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 14, padding: '10px 10px 10px 14px', borderRadius: 20, border: '1.5px dashed var(--blue-dash)', animation: 'rowIn .5s var(--ease-row) both' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 1, flex: 1, minWidth: 0 }}><span style={{ fontSize: 15, fontWeight: 600 }}>Track “{canonical(c.label)}”?</span><span style={{ fontSize: 12.5, color: 'var(--ink-3)' }}>You mentioned it</span></div>
              <button onClick={() => decide(c, 'yes')} aria-label="Track" style={{ flex: 'none', width: 38, height: 38, borderRadius: 19, border: 'none', background: 'var(--blue)', color: '#FFFFFF', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}><Icon d={IC.check} size={16} stroke={2.6} /></button>
              <button onClick={() => decide(c, 'no')} aria-label="Skip" style={{ flex: 'none', width: 38, height: 38, borderRadius: 19, border: 'none', background: 'var(--bg)', color: 'var(--ink-3)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}><Icon d={IC.x} size={14} stroke={2.6} /></button>
            </div>
          ))}
          {typing ? (
            <textarea rows={4} value={typed} onChange={(e) => setTyped(e.target.value)} placeholder="What happened, in your own words" style={{ width: '100%', marginTop: 16, padding: 12, borderRadius: 14, border: '1px solid var(--hair)', background: 'var(--bg)', fontSize: 15, resize: 'none' }} />
          ) : (
            <button onClick={() => setTyping(true)} style={{ marginTop: 18, border: 'none', background: 'transparent', color: 'var(--blue)', fontSize: 14, fontWeight: 600, padding: 0, cursor: 'pointer' }}>Type instead</button>
          )}
          {status && <div style={{ marginTop: 10, fontSize: 12.5, color: 'var(--ink-3)' }}>{status}</div>}
        </div>
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: 120, background: 'linear-gradient(rgba(255,255,255,0),#FFFFFF 40%)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', left: 18, right: 18, bottom: 'var(--safe-bottom)', height: 68, display: 'flex', gap: 10 }}>
        <button onClick={() => setMuted((m) => !m)} disabled={mock} aria-label="Pause or resume listening" style={{ flex: 'none', width: 68, borderRadius: 34, border: 'none', background: 'var(--blue-soft)', color: 'var(--blue)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
          {muted || mock ? <Icon d={IC.mic} size={24} stroke={2} /> : <EqBars fast={speaking} />}
        </button>
        <button className="press" onClick={() => void save()} disabled={saving} style={{ flex: 1, borderRadius: 34, border: 'none', background: 'var(--blue)', color: '#FFFFFF', fontSize: 20, fontWeight: 650, boxShadow: '0 6px 16px oklch(0.53 0.2 257 / .3)', opacity: saving ? 0.7 : 1 }}>{saving ? 'Saving…' : 'Save to diary'}</button>
      </div>
    </div>
  );
}

const Label = ({ children }: { children: string }) => <span style={{ display: 'block', marginTop: 14, fontSize: 12, fontWeight: 700, color: 'var(--ink-3)', letterSpacing: '.05em' }}>{children}</span>;
const Nothing = () => <span style={{ display: 'block', marginTop: 8, fontSize: 14, color: 'var(--ink-4)' }}>Nothing yet</span>;

function WhiteOrb({ active, talking }: { active: boolean; talking: boolean }) {
  return (
    <span style={{ position: 'relative', width: 40, height: 40, display: 'inline-block', flex: 'none' }}>
      {[0, 1].map((i) => <span key={i} style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: 'rgba(255,255,255,.35)', animation: active ? `halo ${talking ? 1.3 : 2.4}s ${i * (talking ? 0.65 : 1.2)}s ease-out infinite` : 'none' }} />)}
      <span style={{ position: 'absolute', inset: 4, borderRadius: '50%', background: 'radial-gradient(circle at 38% 32%, #FFFFFF, rgba(255,255,255,.75) 70%)', boxShadow: '0 4px 16px rgba(0,0,0,.15)', animation: `breathe2 ${talking ? 1 : 2.6}s ease-in-out infinite` }} />
    </span>
  );
}

function EqBars({ fast }: { fast: boolean }) {
  return (
    <span style={{ display: 'inline-flex', gap: 4, alignItems: 'center', height: 22 }}>
      {[0, 1, 2, 3].map((i) => <span key={i} style={{ width: 4, height: 22, borderRadius: 2, background: 'var(--blue)', animation: `eq ${fast ? 0.8 : 1.6}s ${i * 0.14}s ease-in-out infinite` }} />)}
    </span>
  );
}
