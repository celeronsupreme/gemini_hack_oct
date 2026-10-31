// Trigger lab: the five-rung ladder. Lack of data is never a verdict; every card says what would move it.
import { useEffect, useState } from 'react';
import type { AnalysisAnswer, ContextTag, TriggerKind } from '@seizure/contracts';
import { api } from '@/api/client';
import { useStore } from '@/state/store';

const RUNG_LABEL: Record<string, string> = { supported: 'Supported', emerging: 'Emerging', watching: 'Watching', not_seen_so_far: 'Not seen so far', unlikely: 'Unlikely' };
const TAGS: ContextTag[] = ['shower_bath', 'hot', 'cold', 'exercise', 'travel', 'upset', 'school', 'unwell', 'period', 'hungry', 'screen', 'late_night', 'other'];

export function Triggers() {
  const { triggers, loadTriggers } = useStore();
  const [name, setName] = useState('');
  const [kind, setKind] = useState<TriggerKind>('exposure');
  const [tag, setTag] = useState<ContextTag | ''>('');
  const [busy, setBusy] = useState(false);
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<AnalysisAnswer | null>(null);
  useEffect(() => { void loadTriggers(); }, [loadTriggers]);

  const add = async () => {
    if (!name) return;
    setBusy(true);
    try { await api.addTrigger({ name, kind, context_tag: tag || null }); setName(''); await loadTriggers(); } finally { setBusy(false); }
  };
  const ask = async () => {
    if (!question) return;
    setBusy(true);
    try { setAnswer(await api.ask(question)); } finally { setBusy(false); }
  };

  return (
    <div className="screen">
      <h1>Trigger lab</h1>
      <div className="muted">Suggest anything. It is tested on your own log and placed on a ladder: watching → emerging → supported. Nothing is rejected for lack of data.</div>
      <div className="card">
        <label>Test a new trigger or warning sign</label>
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. after the train, eyes going funny" />
        <div className="row" style={{ marginTop: 8 }}>
          <select value={kind} onChange={(e) => setKind(e.target.value as TriggerKind)}>
            <option value="exposure">something that happened (exposure)</option>
            <option value="symptom">a warning sign (symptom)</option>
            <option value="daily_factor">a daily factor (stress, sleep…)</option>
          </select>
          <select value={tag} onChange={(e) => setTag(e.target.value as ContextTag | '')}>
            <option value="">no tag</option>
            {TAGS.map((t) => <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
          </select>
        </div>
        <button className="btn primary" style={{ marginTop: 8, width: '100%' }} disabled={busy || !name} onClick={() => void add()}>Test it</button>
      </div>
      <div className="list">
        {triggers.map((t) => (
          <details key={t.trigger_id} className="card">
            <summary className="row"><b className="grow">{t.trigger}</b><span className={`rung ${t.rung}`}>{RUNG_LABEL[t.rung] ?? t.rung}</span>{t.ratio !== null && t.ratio !== undefined && <span className="chip">{t.ratio.toFixed(1)}×</span>}</summary>
            <p style={{ margin: '8px 0 4px' }}>{t.plain_text}</p>
            <p className="muted" style={{ margin: 0 }}>Next: {t.next_step}</p>
            {t.confounder_note && <p className="muted">{t.confounder_note}</p>}
            <p className="muted" style={{ fontSize: 12 }}>{t.exposure_units} exposures · {t.seizures_exposed} seizures after · p {t.p_adjusted ?? '—'} ({t.tests_corrected_for} tests corrected) · {t.method}</p>
            <button className="btn ghost" onClick={async () => { await api.archiveTrigger(t.trigger_id); await loadTriggers(); }}>Archive</button>
          </details>
        ))}
      </div>
      <h2>Ask the diary</h2>
      <div className="card">
        <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Has moving the afternoon dose helped?" />
        <button className="btn" style={{ marginTop: 8, width: '100%' }} disabled={busy || !question} onClick={() => void ask()}>Ask</button>
        {answer && (
          <div style={{ marginTop: 10 }}>
            <p>{answer.answer}</p>
            {answer.chart_png_base64 && <img alt="chart" style={{ width: '100%' }} src={`data:image/png;base64,${answer.chart_png_base64}`} />}
            {answer.caveats.map((c, i) => <div className="muted" key={i}>{c}</div>)}
            <div className="muted">{answer.model}{answer.mock ? ' (mock)' : ''}</div>
          </div>
        )}
      </div>
    </div>
  );
}
