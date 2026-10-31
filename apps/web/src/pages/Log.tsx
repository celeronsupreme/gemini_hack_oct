// Voice debrief. Live session when Gemini is configured; typed transcript otherwise. Either way the transcript goes
// through /transcripts/extract and the user confirms the record before /transcripts/commit saves it.
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type { DiaryEntryBatch, SeizureEvent } from '@seizure/contracts';
import { api } from '@/api/client';
import { LiveSession, type LiveEvent } from '@/live/liveClient';
import { useStore } from '@/state/store';

const DEMO_LINE = "She had one about quarter past seven, maybe a minute and a half, her head went to the side, she'd just got out of the shower.";

const hhmm = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
const mmss = (s: number) => (s >= 60 ? `${Math.floor(s / 60)} min ${s % 60} s` : `${s} s`);

export function Log() {
  const [params] = useSearchParams();
  const eventId = params.get('event');
  const nav = useNavigate();
  const loadHome = useStore((s) => s.loadHome);
  const session = useRef<LiveSession | null>(null);
  const [status, setStatus] = useState('Tap the microphone and say what happened.');
  const [live, setLive] = useState(false);
  const [lines, setLines] = useState<{ role: 'user' | 'model'; text: string }[]>([]);
  const [typed, setTyped] = useState('');
  const [batch, setBatch] = useState<DiaryEntryBatch | null>(null);
  const [toolSaves, setToolSaves] = useState<string[]>([]);
  const [toolEventIds, setToolEventIds] = useState<string[]>([]); // seizures log_seizure already wrote this session
  const [timed, setTimed] = useState<SeizureEvent | null>(null); // the event the one-tap timer created, if any
  const [busy, setBusy] = useState(false);

  useEffect(() => () => { void session.current?.stop(); }, []);
  useEffect(() => {
    if (!eventId) { setTimed(null); return; }
    void api.events(new Date(Date.now() - 2 * 86400_000).toISOString()).then((evs) => setTimed(evs.find((e) => e.id === eventId) ?? null));
  }, [eventId]);

  const opener = timed
    ? `Tell me about the one at ${hhmm(timed.start_time)}${timed.duration_s ? ` (${mmss(timed.duration_s)}, timed)` : ''}. What happened?`
    : "I'm listening. What happened?";

  const onEvent = (e: LiveEvent) => {
    if (e.type === 'status') setStatus(e.text);
    if (e.type === 'error') setStatus(`Error: ${e.text}`);
    if (e.type === 'user_text' || e.type === 'model_text') setLines([...(session.current?.transcript ?? [])]);
    if (e.type === 'tool') {
      setToolSaves((s) => [...s, `${e.name}: ${JSON.stringify(e.response.say ?? e.response.status ?? '')}`]);
      const id = e.response.event_id;
      if (e.name === 'log_seizure' && typeof id === 'string') setToolEventIds((ids) => (ids.includes(id) ? ids : [...ids, id]));
    }
  };

  const startLive = async () => {
    const s = new LiveSession(); s.onEvent = onEvent; session.current = s;
    setLive(true);
    try { await s.start(eventId ?? undefined); } catch (err) { setStatus(String(err)); setLive(false); }
  };
  const finish = async () => {
    setBusy(true);
    const spoken = session.current && session.current.transcript.length ? session.current.transcriptText() : `Carer: ${typed}`;
    // Give the extractor the facts the timer already knows, and the question the app asked on screen.
    const context = timed
      ? `App: Seizure logged with the timer button, started ${timed.start_time}${timed.duration_s ? `, lasted ${timed.duration_s} seconds (timed, exact)` : ''}.\n`
      : '';
    await session.current?.stop(); setLive(false);
    try {
      const b = await api.extract(`${context}Assistant: ${opener}\n${spoken}`);
      if (timed && b.seizures[0]) {
        // The timer is ground truth for when it started and how long it lasted.
        b.seizures[0] = { ...b.seizures[0], start_time: timed.start_time, ...(timed.duration_s ? { duration_s: timed.duration_s, duration_estimated: false } : {}) };
      }
      setBatch(b); setStatus('Check the record, then save.');
    } catch (err) { setStatus(String(err)); }
    setBusy(false);
  };
  const confirm = async () => {
    if (!batch) return;
    setBusy(true);
    try {
      // Update the timed event, or the row log_seizure wrote mid-conversation, rather than adding a duplicate.
      const target = eventId ?? toolEventIds[0];
      if (target && batch.seizures[0]) {
        const s = batch.seizures[0];
        await api.patchEvent(target, { start_time: s.start_time, type: s.type, severity: s.severity, duration_s: s.duration_s, duration_estimated: s.duration_estimated, context_tags: s.context_tags, notes: s.notes, warning_before: s.warning_before, awareness: s.awareness, rescue_med: s.rescue_med, confidence: s.confidence, still_going: false, source: 'voice' });
        if (batch.seizures.length > 1) await api.commit({ ...batch, seizures: batch.seizures.slice(1) });
      } else {
        await api.commit(batch);
      }
      await loadHome(); nav('/');
    } catch (err) { setStatus(String(err)); }
    setBusy(false);
  };
  const update = (i: number, patch: Partial<SeizureEvent>) => {
    if (!batch) return;
    const seizures = batch.seizures.map((s, j) => (j === i ? { ...s, ...patch } : s));
    setBatch({ ...batch, seizures });
  };

  return (
    <div className="screen">
      <h1>{eventId ? 'Tell me about it' : 'Log by voice'}</h1>
      {timed && (
        <div className="card row">
          <b className="grow">Timed: started {hhmm(timed.start_time)}</b>
          <span className="chip">{timed.duration_s ? mmss(timed.duration_s) : 'not timed'}</span>
        </div>
      )}
      <div className="muted">{status}</div>
      {!batch && (
        <>
          <div className="transcript card">
            <div className="bubble model">{opener}</div>
            {lines.length === 0 && <div className="muted">Start talking any time after you tap the mic. It asks one question at a time for anything missing.</div>}
            {lines.map((l, i) => <div key={i} className={`bubble ${l.role}`}>{l.text}</div>)}
          </div>
          {toolSaves.length > 0 && <div className="card"><b>Saved during the conversation</b><ul>{toolSaves.map((t, i) => <li key={i}>{t}</li>)}</ul></div>}
          <div className="row">
            {!live ? <button className="btn primary grow" onClick={() => void startLive()}>🎤 Start listening</button>
                  : <button className="btn primary grow" disabled={busy} onClick={() => void finish()}>Finish and check the record</button>}
          </div>
          <details className="card">
            <summary>Or type what happened</summary>
            <textarea rows={4} value={typed} onChange={(e) => setTyped(e.target.value)} placeholder={DEMO_LINE} />
            <div className="row" style={{ marginTop: 8 }}>
              <button className="btn ghost" onClick={() => setTyped(DEMO_LINE)}>Use demo line</button>
              <button className="btn primary grow" disabled={!typed || busy} onClick={() => void finish()}>Extract record</button>
            </div>
          </details>
        </>
      )}
      {batch && (
        <>
          {batch.seizures.map((s, i) => (
            <div className="card" key={i}>
              <b>Seizure {i + 1}</b>
              <div className="record" style={{ marginTop: 8 }}>
                <span className="k">Start</span><input type="datetime-local" value={s.start_time.slice(0, 16)} onChange={(e) => update(i, { start_time: new Date(e.target.value).toISOString() })} />
                <span className="k">Duration (s)</span><input type="number" value={s.duration_s ?? ''} onChange={(e) => update(i, { duration_s: e.target.value ? Number(e.target.value) : null })} />
                <span className="k">Type</span>
                <select value={s.type} onChange={(e) => update(i, { type: e.target.value as SeizureEvent['type'], severity: ['impaired_awareness', 'convulsive', 'drop'].includes(e.target.value) ? 'severe' : 'mild' })}>
                  {['aware', 'staring', 'impaired_awareness', 'convulsive', 'drop', 'jerk', 'unsure'].map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
                </select>
                <span className="k">Warning before</span><span className="v">{s.warning_before === true ? 'yes' : s.warning_before === false ? 'no' : 'not said'}</span>
                <span className="k">Context</span><span className="v">{s.context_tags?.join(', ') || '—'}</span>
                <span className="k">Rescue med</span><span className="v">{s.rescue_med ? `${s.rescue_med.drug} ${s.rescue_med.dose_mg ?? ''}` : '—'}</span>
                <span className="k">Confidence</span><span className="v">{s.confidence}{s.duration_estimated ? ' · duration estimated' : ''}</span>
              </div>
              {s.notes && <div className="muted" style={{ marginTop: 8 }}>{s.notes}</div>}
            </div>
          ))}
          {batch.open_questions.length > 0 && <div className="card"><b>Still unknown</b><ul>{batch.open_questions.map((q, i) => <li key={i}>{q}</li>)}</ul></div>}
          <div className="row">
            <button className="btn ghost" onClick={() => setBatch(null)}>Back</button>
            <button className="btn primary grow" disabled={busy} onClick={() => void confirm()}>Looks right — save</button>
          </div>
        </>
      )}
    </div>
  );
}
