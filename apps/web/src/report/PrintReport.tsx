// The clinic report as printed (A4). Page 1 follows the plan's NICE/AAN shape: counts first, per-28-day rates,
// completeness, risk factors as facts. Appendix sections are the export switches.
import type { ClinicReport, Profile, SeizureEvent } from '@seizure/contracts';
import { durTxt, hhmm } from '@/ui/format';

const S = {
  page: { fontFamily: 'var(--font)', color: '#000', fontSize: 10.5, lineHeight: 1.35 } as React.CSSProperties,
  h1: { fontSize: 18, fontWeight: 700, margin: '0 0 2px' } as React.CSSProperties,
  h2: { fontSize: 12, fontWeight: 700, margin: '12px 0 4px', borderBottom: '1px solid #999', paddingBottom: 2 } as React.CSSProperties,
  table: { width: '100%', borderCollapse: 'collapse', fontSize: 9.5 } as React.CSSProperties,
  td: { borderBottom: '0.5px solid #ccc', padding: '2px 4px', textAlign: 'left', verticalAlign: 'top' } as React.CSSProperties,
  kpi: { display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 6, marginTop: 6 } as React.CSSProperties,
  box: { border: '1px solid #bbb', borderRadius: 4, padding: 5 } as React.CSSProperties,
};

export function PrintReport({ rep, events, profile, include }: { rep: ClinicReport; events: SeizureEvent[]; profile: Profile | null; include: { log: boolean; plan: boolean; trig: boolean; q: boolean } }) {
  const h = rep.headline;
  const plan = profile?.rescue_plan;
  const kpis: [string | number, string][] = [
    [h.total, 'seizures'],
    [h.per_28_days, `per 28 days${h.pct_change != null ? ` (${h.pct_change > 0 ? '+' : ''}${h.pct_change}% vs prior)` : ''}`],
    [h.seizure_days, 'seizure days'],
    [h.days_since_last_convulsive ?? '—', 'days since last tonic-clonic'],
    [h.longest_seizure_free_run_days, 'longest run with none logged (days)'],
    [rep.events_ge_5min, 'of 5 min or more'],
  ];
  return (
    <div style={S.page}>
      <h1 style={S.h1}>Clinic report{profile?.display_name ? ` · ${profile.display_name}` : ''}</h1>
      <div>{rep.window_start} to {rep.window_end} (prior window {rep.prior_window_start} to {rep.prior_window_end}) · generated {new Date(rep.generated_at).toLocaleDateString('en-GB')}</div>
      <div>Completeness: {rep.completeness.days_with_any_entry} of {rep.completeness.days_in_window} days have an entry; logged by {Object.entries(rep.completeness.logged_by).map(([k, v]) => `${k} ${v}`).join(', ') || '—'}. Days without an entry are not counted as seizure-free.</div>
      <div style={S.kpi}>{kpis.map(([v, l]) => <div key={l} style={S.box}><b style={{ fontSize: 14, display: 'block' }}>{v}</b>{l}</div>)}</div>

      <h2 style={S.h2}>By type (ILAE 2017; the family’s label in brackets)</h2>
      <table style={S.table}><thead><tr>{['Type', 'Count', '/28 d', 'Prior', 'Median s', 'Max s', '≥5 min', 'Last'].map((c) => <th key={c} style={S.td}>{c}</th>)}</tr></thead>
        <tbody>{rep.by_type.map((t) => <tr key={t.type}><td style={S.td}>{t.ilae_name}{t.patient_label ? ` (${t.patient_label})` : ''}</td><td style={S.td}>{t.count}</td><td style={S.td}>{t.per_28_days}</td><td style={S.td}>{t.prior_count}</td><td style={S.td}>{t.median_duration_s ?? '—'}</td><td style={S.td}>{t.max_duration_s ?? '—'}</td><td style={S.td}>{t.count_ge_5min}</td><td style={S.td}>{t.last_seen ?? '—'}</td></tr>)}</tbody></table>
      <div style={{ marginTop: 3 }}>Cluster definition: {rep.cluster_definition}. Cluster days: {rep.cluster_days}. Night-time seizures, last 30 days: {rep.nocturnal_count_30d}. Tonic-clonic, last 12 months: {rep.convulsive_count_12m}.</div>

      <h2 style={S.h2}>Medication</h2>
      <div>{rep.medication.current.map((m) => `${m.drug} ${m.dose_mg} mg at ${m.times.join(', ')}`).join(' · ') || 'None on file'}</div>
      <div>Adherence: {rep.medication.adherence_pct != null ? `${rep.medication.adherence_pct}% of logged doses taken` : 'dose logging not in use'} · missed doses: {rep.medication.missed_doses} · rescue uses in window: {rep.medication.rescue_uses.length}</div>
      {rep.medication.changes.length > 0 && (
        <table style={{ ...S.table, marginTop: 4 }}><thead><tr>{['Date', 'Change', 'Before → after /wk', 'Verdict'].map((c) => <th key={c} style={S.td}>{c}</th>)}</tr></thead>
          <tbody>{rep.medication.changes.slice(-6).reverse().map((c, i) => <tr key={i}><td style={S.td}>{c.date}</td><td style={S.td}>{c.drug} {c.action}: {c.detail.slice(0, 70)}</td><td style={S.td}>{c.before_per_week ?? '—'} → {c.after_per_week ?? '—'}</td><td style={S.td}>{c.verdict}</td></tr>)}</tbody></table>
      )}

      <h2 style={S.h2}>Risk factors (facts, not a score)</h2>
      <table style={S.table}><tbody>{rep.risk_factors.map((r) => <tr key={r.factor}><td style={{ ...S.td, width: 14 }}>{r.present === true ? '✔' : r.present === false ? '✘' : '?'}</td><td style={S.td}>{r.factor}</td><td style={S.td}>{r.detail}</td></tr>)}</tbody></table>

      {include.trig && rep.triggers.length > 0 && (<><h2 style={S.h2}>Trigger lab (supported and emerging only)</h2><ul style={{ margin: 0, paddingLeft: 16 }}>{rep.triggers.map((t) => <li key={t.trigger_id}>{t.trigger}: {t.plain_text}</li>)}</ul></>)}
      {include.q && (<><h2 style={S.h2}>Questions for the clinic</h2>{rep.questions_for_clinician.length ? <ol style={{ margin: 0, paddingLeft: 16 }}>{rep.questions_for_clinician.map((q, i) => <li key={i}>{q}</li>)}</ol> : <div>None written yet.</div>}</>)}
      <div style={{ marginTop: 8, fontSize: 8.5, color: '#444' }}>{rep.logging_effort_note} {rep.wording_notes.join(' ')} Research prototype; not a medical device.</div>

      {include.plan && plan && (
        <div style={{ breakBefore: 'page' }}>
          <h2 style={S.h2}>Emergency care plan</h2>
          <div>Call {(plan.call?.length ? plan.call : ['999']).join(' or ')} if a convulsive seizure passes {plan.emergency_minutes_convulsive} minutes, any seizure passes {plan.emergency_minutes_other} minutes or is longer than usual, a second one starts before recovery, breathing is affected, or there is injury or water.</div>
          {plan.rescue_drug && <div>Rescue medicine: {plan.rescue_drug} {plan.rescue_dose_mg ?? ''} mg. {plan.notes ?? ''}</div>}
        </div>
      )}
      {include.log && events.length > 0 && (
        <div style={{ breakBefore: 'page' }}>
          <h2 style={S.h2}>Event log ({events.length})</h2>
          <table style={S.table}><thead><tr>{['Date', 'Time', 'Type', 'Length', 'Before it', 'Source'].map((c) => <th key={c} style={S.td}>{c}</th>)}</tr></thead>
            <tbody>{[...events].reverse().map((e) => <tr key={e.id}><td style={S.td}>{e.start_time.slice(0, 10)}</td><td style={S.td}>{hhmm(e.start_time)}</td><td style={S.td}>{e.original_label || e.type.replace('_', ' ')}</td><td style={S.td}>{durTxt(e.duration_s) || '—'}</td><td style={S.td}>{[...(e.context_tags ?? []), ...(e.factors ?? [])].join(', ')}</td><td style={S.td}>{e.synthetic ? 'demo data' : e.source}</td></tr>)}</tbody></table>
        </div>
      )}
    </div>
  );
}
