// Voice debrief. Live session when Gemini is configured; typed transcript otherwise. Either way the transcript goes
// through /transcripts/extract and the user confirms the record before /transcripts/commit saves it.
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type { DiaryEntryBatch, SeizureEvent } from '@seizure/contracts';
import { api } from '@/api/client';
import { LiveSession, type LiveEvent } from '@/live/liveClient';
import { useStore } from '@/state/store';

const DEMO_LINE = "She had one about quarter past seven, maybe a minute and a half, her head went to the side, she'd just got out of the shower.";

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
  const [busy, setBusy] = useState(false);

  useEffect(() => () => { void session.current?.stop(); }, []);

  const onEvent = (e: LiveEvent) => {
    if (e.type === 'status') setStatus(e.text);
    if (e.type === 'error') setStatus(`Error: ${e.text}`);
    if (e.type === 'user_text' || e.type === 'model_text') setLines([...(session.current?.transcript ?? [])]);
    if (e.type === 'tool') setToolSaves((s) => [...s, `${e.name}: ${JSON.stringify(e.response.say ?? e.response.status ?? '')}`]);
  };

  const startLive = async () => {
    const s = new LiveSession(); s.onEvent = onEvent; session.current = s;
    await s.start(); setLive(true);
  };
  const finish = async () => {
    setBusy(true);
    const transcript = session.current && session.current.transcript.length ? session.current.transcriptText() : typed;
    await session.current?.stop(); setLive(false);
    try { setBatch(await api.extract(transcript)); setStatus('Check the record, then save.'); } catch (err) { setStatus(String(err)); }
    setBusy(false);
  };
  const confirm = async () => {
    if (!batch) return;
    setBusy(true);
    try {
      if (eventId && batch.seizures[0]) {
        const s = batch.seizures[0];
        await api.patchEvent(eventId, { type: s.type, severity: s.severity, duration_s: s.duration_s, duration_estimated: s.duration_estimated, context_tags: s.context_tags, notes: s.notes, warning_before: s.warning_before, awareness: s.awareness, rescue_med: s.rescue_med, confidence: s.confidence, source: 'voice' });
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
      <div className="muted">{status}</div>
      {!batch && (
        <>
          <div className="transcript card">
            {lines.length === 0 && <div className="muted">Transcript appears here. The assistant asks one question at a time for anything missing.</div>}
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
