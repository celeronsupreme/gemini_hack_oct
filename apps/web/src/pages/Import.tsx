// Onboarding door two: import a spreadsheet. Preview the proposed mapping and assumptions, then commit.
import { useState } from 'react';
import type { ImportPreview } from '@seizure/contracts';
import { api } from '@/api/client';
import { useStore } from '@/state/store';

export function Import() {
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<string | null>(null);
  const loadHome = useStore((s) => s.loadHome);
  const onFile = async (f: File | undefined) => { if (!f) return; setBusy(true); try { setPreview(await api.importPreview(f)); } finally { setBusy(false); } };
  const commit = async (replace: boolean) => {
    if (!preview) return;
    setBusy(true);
    try { const r = await api.importCommit(preview.job_id, preview.label_mapping, replace); setDone(`${r.imported} seizures imported.`); setPreview(null); await loadHome(); } finally { setBusy(false); }
  };
  return (
    <div className="screen">
      <h1>Import a diary</h1>
      <div className="muted">A spreadsheet (.xlsx) or CSV. The mapping is proposed, you confirm it. Names in notes are replaced with role words before anything is stored.</div>
      <input type="file" accept=".xlsx,.csv" onChange={(e) => void onFile(e.target.files?.[0])} disabled={busy} />
      {done && <div className="card">{done}</div>}
      {preview && (
        <>
          <div className="card">
            <b>{preview.source_name}</b> · {preview.total_rows} rows
            <table style={{ width: '100%', fontSize: 13, marginTop: 8 }}><tbody>{Object.entries(preview.column_mapping).map(([k, v]) => <tr key={k}><td>{k}</td><td>→ {v}</td></tr>)}</tbody></table>
            <ul className="muted">{preview.assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul>
            {preview.warnings.map((w, i) => <div className="error" key={i}>{w}</div>)}
          </div>
          <div className="card">
            <b>Type labels found</b>
            <ul>{Object.entries(preview.label_mapping).slice(0, 12).map(([k, v]) => <li key={k}>{k} → {v.replace('_', ' ')}</li>)}</ul>
          </div>
          <div className="row">
            <button className="btn grow" disabled={busy} onClick={() => void commit(false)}>Add to diary</button>
            <button className="btn primary grow" disabled={busy} onClick={() => void commit(true)}>Replace diary</button>
          </div>
        </>
      )}
    </div>
  );
}
