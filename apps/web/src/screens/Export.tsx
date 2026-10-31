// Export sheet (from Account): PDF clinic report or CSV data, for since-last-visit / 90 days / 12 months, each beside
// the same-length prior window. The PDF is the print-only page in report/PrintReport, printed by the browser.
import { useState } from 'react';
import { createRoot, type Root } from 'react-dom/client';
import { flushSync } from 'react-dom';
import type { ClinicReport, SeizureEvent } from '@seizure/contracts';
import { api } from '@/api/client';
import { herOf, useStore } from '@/state/store';
import { PrintReport } from '@/report/PrintReport';
import { Icon, IC } from '@/ui/icons';
import { SheetHead } from './Account';

type Win = 'last' | '90' | '365';
type Inc = { log: boolean; plan: boolean; trig: boolean; q: boolean };
let printRoot: Root | null = null;

export function ExportSheet({ fmt: initial, onClose }: { fmt: 'pdf' | 'csv'; onClose: () => void }) {
  const { profile, flash } = useStore();
  const her = herOf(profile);
  const [fmt, setFmt] = useState(initial);
  const [win, setWin] = useState<Win>(profile?.last_appointment ? 'last' : '90');
  const [inc, setInc] = useState<Inc>({ log: true, plan: true, trig: true, q: true });
  const [busy, setBusy] = useState(false);
  const pdf = fmt === 'pdf';
  const sinceLast = profile?.last_appointment ? Math.max(1, Math.min(400, Math.round((Date.now() - new Date(profile.last_appointment).getTime()) / 86400_000))) : null;
  const days = win === 'last' ? sinceLast ?? 90 : Number(win);
  const WIN: Record<Win, [string, string]> = {
    last: ['Since last visit', sinceLast ? `Since ${her} last appointment, beside the same length before it` : `No appointment date on file yet, so the last 90 days, beside the 90 before`],
    '90': ['90 days', 'The last 90 days, beside the 90 before'],
    '365': ['12 months', 'The last 12 months, beside the year before'],
  };
  const INC: [keyof Inc, string, string][] = [['log', 'Event log', 'Every seizure in the window, as an appendix'], ['plan', 'Emergency care plan', 'Rescue plan, 999 rules, who to call'], ['trig', 'Trigger lab', 'Supported and emerging triggers only'], ['q', `${her === 'her' ? 'Her' : 'Your'} questions`, 'Three questions to raise at the visit']];
  const since = new Date(Date.now() - days * 86400_000).toISOString();

  const doExport = async () => {
    setBusy(true);
    try {
      if (pdf) {
        const [rep, events] = await Promise.all([api.clinicReport(days), inc.log ? api.events(since, undefined, 5000) : Promise.resolve([] as SeizureEvent[])]);
        printReport(rep, events, inc);
        onClose(); flash('Clinic report saved · PDF');
      } else {
        const [events, doses, checkins] = await Promise.all([api.events(since, undefined, 5000), api.doses(since), api.checkins(since)]);
        download('seizures.csv', toCsv(events.map((e) => ({ date: e.start_time.slice(0, 10), start_time: e.start_time, duration_s: e.duration_s, type: e.type, awareness: e.awareness, what_happened: e.original_label, context_tags: (e.context_tags ?? []).join(';'), factors: (e.factors ?? []).join(';'), recovery: e.recovery_text, notes: e.notes, rescue: e.rescue_med ? `${e.rescue_med.drug} ${e.rescue_med.dose_mg ?? ''}` : '', source: e.source, demo_data: e.synthetic ? 'yes' : '' }))));
        download('doses.csv', toCsv(doses.map((d) => ({ drug: d.drug, dose_mg: d.dose_mg, scheduled_time: d.scheduled_time, taken_time: d.taken_time, skipped: d.skipped, reason: d.reason }))));
        download('checkins.csv', toCsv(checkins.map((c) => ({ ...c, daily_trigger_flags: JSON.stringify(c.daily_trigger_flags ?? {}) }))));
        onClose(); flash('Diary exported · CSV');
      }
    } catch (e) { flash(`Export failed: ${String(e).slice(0, 60)}`); }
    setBusy(false);
  };

  return (
    <>
      <SheetHead title="Export" onClose={onClose} action="Cancel" />
      <div className="scr" style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '4px 16px 120px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div style={{ padding: '0 4px', display: 'flex', flexDirection: 'column', gap: 3 }}>
          <span style={{ fontSize: 28, fontWeight: 700, letterSpacing: '-0.025em' }}>{pdf ? 'Clinic report' : `${her === 'her' ? 'Her' : 'Your'} diary`}</span>
          <span style={{ fontSize: 14, lineHeight: 1.4, color: 'var(--ink-3)' }}>{pdf ? 'One A4 page in the shape a neurologist expects, with an optional appendix.' : `All of ${her} data as spreadsheets, to keep or move to another app.`}</span>
        </div>
        <div className="card" style={{ padding: '14px 16px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}><span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-3)' }}>Format</span>
            <div className="seg">{(['pdf', 'csv'] as const).map((k) => <button key={k} className={fmt === k ? 'on' : ''} onClick={() => setFmt(k)}>{k === 'pdf' ? 'PDF report' : 'CSV data'}</button>)}</div></div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}><span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink-3)' }}>Covers</span>
            <div className="seg">{(['90', '365', 'last'] as Win[]).map((k) => <button key={k} className={win === k ? 'on' : ''} onClick={() => setWin(k)} style={{ fontSize: 13.5 }}>{WIN[k][0]}</button>)}</div>
            <span style={{ fontSize: 12.5, color: 'var(--ink-3)' }}>{WIN[win][1]}</span></div>
        </div>
        {pdf ? (
          <>
            <div className="card" style={{ padding: 16, display: 'flex', gap: 16, alignItems: 'flex-start' }}>
              <div style={{ flex: 'none', width: 118, height: 166, borderRadius: 6, background: '#FFFFFF', boxShadow: '0 0 0 1px rgba(60,60,67,.14), 0 6px 16px rgba(0,0,0,.08)', padding: '10px 9px', display: 'flex', flexDirection: 'column', gap: 6 }}>
                <span style={{ fontSize: 7.5, fontWeight: 700 }}>Clinic report{profile?.display_name ? ` · ${profile.display_name}` : ''}</span>
                <div style={{ display: 'flex', gap: 3 }}>{[0, 1, 2].map((i) => <span key={i} style={{ flex: 1, height: 18, borderRadius: 3, background: 'var(--blue-soft)' }} />)}</div>
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height: 26 }}>{[40, 65, 50, 85, 55, 70].map((h, i) => <span key={i} style={{ flex: 1, height: `${h}%`, background: i === 3 ? 'var(--blue)' : 'var(--blue-mid)' }} />)}</div>
                {[90, 70, 80, 60, 85].map((w, i) => <span key={i} style={{ height: 3, width: `${w}%`, borderRadius: 2, background: 'var(--fill-2)' }} />)}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 7, fontSize: 13.5, lineHeight: 1.3, color: 'var(--ink-2)', paddingTop: 2 }}>
                <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--ink)' }}>Page 1</span>
                <span>Seizures per 28 days, by type</span><span>Medicines, doses missed, changes</span><span>Night-time and convulsive counts</span><span>How complete the diary is</span>
              </div>
            </div>
            <div className="group" style={{ margin: 0 }}>
              {INC.map(([k, label, sub], i) => (
                <div key={k} className={i ? 'hair-top' : ''} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '11px 0' }}>
                  <span style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 1 }}><span style={{ fontSize: 15.5, fontWeight: 600 }}>{label}</span><span style={{ fontSize: 12.5, color: 'var(--ink-3)' }}>{sub}</span></span>
                  <button className={`switch${inc[k] ? ' on' : ''}`} aria-pressed={inc[k]} aria-label={label} onClick={() => setInc({ ...inc, [k]: !inc[k] })}><span /></button>
                </div>
              ))}
            </div>
          </>
        ) : (
          <>
            <div className="group" style={{ margin: 0 }}>
              {[['seizures.csv', 'Time, length, type, triggers, notes'], ['doses.csv', 'Every dose, taken or missed'], ['checkins.csv', 'Sleep, mood, stress, period']].map(([n, s]) => (
                <div key={n} className="lrow" style={{ cursor: 'default' }}><span className="ico" style={{ background: 'var(--blue-soft)', color: 'var(--blue)' }}><Icon d={IC.file} size={18} /></span><span className="txt"><span style={{ fontSize: 15.5, fontWeight: 600 }}>{n}</span><span style={{ fontSize: 12.5, color: 'var(--ink-3)' }}>{s}</span></span></div>
              ))}
            </div>
            <div style={{ padding: '0 6px', fontSize: 12.5, lineHeight: 1.4, color: 'var(--ink-3)' }}>Opens in Excel, Numbers or Google Sheets. Notes are kept word for word.</div>
          </>
        )}
      </div>
      <div className="dock" style={{ position: 'absolute', left: 14, right: 14, bottom: 'var(--safe-bottom)', background: 'rgba(255,255,255,.82)' }}>
        <button className="dock-btn press" onClick={() => void doExport()} disabled={busy} style={{ fontSize: 20, gap: 10, opacity: busy ? 0.7 : 1 }}><Icon d={IC.download} size={20} stroke={2.2} />{busy ? 'Preparing…' : pdf ? 'Export PDF' : 'Export CSV'}</button>
      </div>
    </>
  );
}

function printReport(rep: ClinicReport, events: SeizureEvent[], inc: Inc) {
  const el = document.getElementById('print-root');
  if (!el) return;
  printRoot ??= createRoot(el);
  const { profile } = useStore.getState();
  flushSync(() => printRoot!.render(<PrintReport rep={rep} events={events} profile={profile} include={inc} />));
  setTimeout(() => window.print(), 50);
}

function toCsv(rows: Record<string, unknown>[]): string {
  if (!rows.length) return '';
  const cols = [...new Set(rows.flatMap((r) => Object.keys(r)))];
  const cell = (v: unknown) => { const s = v == null ? '' : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; };
  return [cols.join(','), ...rows.map((r) => cols.map((c) => cell(r[c])).join(','))].join('\n');
}

function download(name: string, text: string) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([text || 'no rows\n'], { type: 'text/csv' }));
  a.download = name; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}
