// Clinic report, page 1 in the NICE/AAN shape: counts first, per-28-day rates, completeness, risk factors as facts.
// "Export PDF" uses the print stylesheet; a server-side PDF can replace it later without changing the data shape.
import { useEffect, useState } from 'react';
import type { ClinicReport } from '@seizure/contracts';
import { api } from '@/api/client';

export function Report() {
  const [rep, setRep] = useState<ClinicReport | null>(null);
  const [window, setWindow] = useState(90);
  const [questions, setQuestions] = useState('');
  useEffect(() => { void api.clinicReport(window).then((r) => { setRep(r); setQuestions(r.questions_for_clinician.join('\n')); }); }, [window]);
  if (!rep) return <div className="screen"><h1>Clinic report</h1><div className="muted">Building…</div></div>;
  const h = rep.headline;
  return (
    <div className="screen report">
      <div className="row noprint">
        <h1 className="grow">Clinic report</h1>
        <select value={window} onChange={(e) => setWindow(Number(e.target.value))} style={{ width: 'auto' }}><option value={28}>28 days</option><option value={90}>90 days</option><option value={180}>180 days</option></select>
        <button className="btn" onClick={() => print()}>Export PDF</button>
      </div>
      <div className="card">
        <div className="muted">{rep.window_start} to {rep.window_end} · prior window {rep.prior_window_start} to {rep.prior_window_end} · generated {new Date(rep.generated_at).toLocaleDateString()}</div>
        <div className="muted">Completeness: {rep.completeness.days_with_any_entry} of {rep.completeness.days_in_window} days have an entry; logged by {Object.entries(rep.completeness.logged_by).map(([k, v]) => `${k} ${v}`).join(', ') || '—'}.</div>
        <div className="kpi" style={{ marginTop: 10 }}>
          <div><b>{h.total}</b>seizures</div>
          <div><b>{h.per_28_days}</b>per 28 days{h.pct_change !== null && h.pct_change !== undefined ? ` (${h.pct_change > 0 ? '+' : ''}${h.pct_change}% vs prior)` : ''}</div>
          <div><b>{h.seizure_days}</b>seizure days</div>
          <div><b>{h.days_since_last_convulsive ?? '—'}</b>days since last tonic-clonic</div>
          <div><b>{h.longest_seizure_free_run_days}</b>longest run without</div>
          <div><b>{rep.events_ge_5min}</b>of 5 min or more</div>
        </div>
      </div>
      <div className="card">
        <b>By type (ILAE 2017 names; the family's label in brackets)</b>
        <table>
          <thead><tr><th>Type</th><th>Count</th><th>/28 d</th><th>Prior</th><th>Median s</th><th>Max s</th><th>Last</th></tr></thead>
          <tbody>{rep.by_type.map((t) => <tr key={t.type}><td>{t.ilae_name}{t.patient_label ? ` (${t.patient_label})` : ''}</td><td>{t.count}</td><td>{t.per_28_days}</td><td>{t.prior_count}</td><td>{t.median_duration_s ?? '—'}</td><td>{t.max_duration_s ?? '—'}</td><td>{t.last_seen ?? '—'}</td></tr>)}</tbody>
        </table>
        <div className="muted">Cluster definition: {rep.cluster_definition}. Cluster days: {rep.cluster_days}. Night-time seizures, last 30 days: {rep.nocturnal_count_30d}. Tonic-clonic, last 12 months: {rep.convulsive_count_12m}.</div>
      </div>
      <div className="card">
        <b>Medication</b>
        <ul>{rep.medication.current.map((m, i) => <li key={i}>{m.drug} {m.dose_mg} mg at {m.times.join(', ')}</li>)}</ul>
        <div className="muted">Adherence: {rep.medication.adherence_pct !== null && rep.medication.adherence_pct !== undefined ? `${rep.medication.adherence_pct}% of logged doses taken` : 'dose logging not in use'} · missed doses: {rep.medication.missed_doses} · rescue uses in window: {rep.medication.rescue_uses.length}</div>
        {rep.medication.changes.length > 0 && (
          <table><thead><tr><th>Date</th><th>Change</th><th>Before → after /wk</th><th>Verdict</th></tr></thead>
            <tbody>{rep.medication.changes.slice(-8).reverse().map((c, i) => <tr key={i}><td>{c.date}</td><td>{c.drug} {c.action}: {c.detail.slice(0, 60)}</td><td>{c.before_per_week ?? '—'} → {c.after_per_week ?? '—'}</td><td>{c.verdict}</td></tr>)}</tbody></table>
        )}
      </div>
      <div className="card">
        <b>Risk factors (facts, not a score)</b>
        <table><tbody>{rep.risk_factors.map((r) => <tr key={r.factor}><td>{r.present === true ? '✔' : r.present === false ? '✘' : '?'}</td><td>{r.factor}</td><td className="muted">{r.detail}</td></tr>)}</tbody></table>
      </div>
      {rep.triggers.length > 0 && (
        <div className="card"><b>Triggers with support in the log</b><ul>{rep.triggers.map((t) => <li key={t.trigger_id}>{t.trigger}: {t.plain_text}</li>)}</ul></div>
      )}
      <div className="card">
        <b>Questions for the clinic</b>
        <textarea rows={3} value={questions} onChange={(e) => setQuestions(e.target.value)} onBlur={() => void api.saveQuestions(questions.split('\n').filter(Boolean))} placeholder="One per line" className="noprint" />
        <ul className="print-only">{questions.split('\n').filter(Boolean).map((q, i) => <li key={i}>{q}</li>)}</ul>
        <div className="muted">{rep.logging_effort_note}</div>
        <div className="muted" style={{ fontSize: 11 }}>{rep.wording_notes.join(' ')}</div>
      </div>
    </div>
  );
}
