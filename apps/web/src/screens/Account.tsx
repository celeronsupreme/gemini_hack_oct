// Account, opened from the avatar. Reports and export first, then her care, then privacy (design order).
import type { Profile } from '@seizure/contracts';
import { herOf, useStore } from '@/state/store';
import { Icon, IC } from '@/ui/icons';

const Chev = () => <span className="chev">›</span>;
function Ico({ d, bg, fg }: { d: string; bg: string; fg: string }) { return <span className="ico" style={{ background: bg, color: fg }}><Icon d={d} /></span>; }

export function Account() {
  const { screen, profile, triggers, go, open, flash, loadTriggers } = useStore();
  const visible = screen === 'account';
  const her = herOf(profile);
  const name = profile?.display_name || (profile?.role === 'self' ? 'My diary' : 'Her diary');
  const meds = [...new Set((profile?.medications ?? []).filter((m) => !m.as_needed).map((m) => m.drug))];
  const blue = ['var(--blue)', '#FFFFFF'] as const, soft = ['var(--blue-soft)', 'var(--blue)'] as const;
  return (
    <div className="screen pushed scr" style={{ zIndex: 12, transform: visible ? 'none' : 'translateX(100%)' }}>
      <div style={{ padding: '6px 12px 0' }}><button className="back" onClick={() => go('home')}><span>‹</span>Today</button></div>
      <div className="large-title">Account</div>
      <div className="card" style={{ margin: '0 16px 22px', display: 'flex', alignItems: 'center', gap: 14 }}>
        <span style={{ flex: 'none', width: 56, height: 56, borderRadius: 28, background: 'var(--avatar)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 23, fontWeight: 600, color: 'var(--ink-2)' }}>{(profile?.display_name || 'H').charAt(0).toUpperCase()}</span>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2, flex: 1, minWidth: 0 }}><span style={{ fontSize: 19, fontWeight: 700 }}>{name}</span><span style={{ fontSize: 14, color: 'var(--ink-3)' }}>{profile?.role === 'carer' ? 'You’re logging as her carer' : 'Your own diary'}</span></div>
        <Chev />
      </div>

      <div className="section-label">REPORTS AND EXPORT</div>
      <div className="group">
        <button className="lrow" onClick={() => open({ kind: 'export', fmt: 'pdf' })}><Ico d={IC.doc} bg={blue[0]} fg={blue[1]} /><span className="txt"><span className="t1">Clinic report</span><span className="t2">One page for {her} neurologist · PDF</span></span><Chev /></button>
        <button className="lrow" onClick={() => open({ kind: 'export', fmt: 'csv' })}><Ico d={IC.download} bg={blue[0]} fg={blue[1]} /><span className="txt"><span className="t1">Export {her} diary</span><span className="t2">Every seizure, dose and check-in · CSV</span></span><Chev /></button>
        <button className="lrow" onClick={() => flash('Link copied · expires in 7 days')}><Ico d={IC.link} bg={soft[0]} fg={soft[1]} /><span className="txt"><span className="t1">Share with {her} nurse</span><span className="t2">Read-only link, expires in 7 days</span></span><Chev /></button>
      </div>

      <div className="section-label">{her === 'her' ? 'HER CARE' : 'YOUR CARE'}</div>
      <div className="group">
        <button className="lrow" onClick={() => open({ kind: 'medicines' })}><Ico d={IC.pill} bg={soft[0]} fg={soft[1]} /><span className="txt"><span className="t1">Medicines</span><span className="t2">{meds.length ? meds.map((m) => m[0].toUpperCase() + m.slice(1)).join(', ') : 'None on file'}</span></span><Chev /></button>
        <button className="lrow" onClick={() => open({ kind: 'emergency' })}><Ico d={IC.cross} bg="var(--emergency-bg)" fg="var(--high-text)" /><span className="txt"><span className="t1">Emergency plan</span><span className="t2">5-minute rule, rescue plan, who to call</span></span><Chev /></button>
        <button className="lrow" onClick={() => { void loadTriggers(); go('trends'); }}><Ico d={IC.flask} bg={soft[0]} fg={soft[1]} /><span className="txt"><span className="t1">Triggers {her === 'her' ? 'she’s' : 'you’re'} testing</span><span className="t2">{triggers.length} tested in {her} trigger lab</span></span><Chev /></button>
      </div>

      <div className="section-label">PRIVACY</div>
      <div className="group" style={{ marginBottom: 14 }}>
        <button className="lrow" onClick={() => open({ kind: 'privacy' })}><Ico d={IC.shield} bg="var(--fill)" fg="var(--ink-2)" /><span className="txt"><span className="t1">What the assistant sees</span><span className="t2">Names and NHS number removed first</span></span><Chev /></button>
        <button className="lrow" onClick={() => flash('Not available in the research prototype')}><Ico d={IC.trash} bg="var(--fill)" fg="var(--danger)" /><span className="txt"><span className="t1" style={{ color: 'var(--danger)' }}>Delete {her} data</span></span></button>
      </div>
      <div className="footnote">Research prototype, not a medical device.</div>
    </div>
  );
}

/** Sheet header shared by the small Account sheets. */
export function SheetHead({ title, onClose, action = 'Done' }: { title: string; onClose: () => void; action?: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 16px 12px 20px', flex: 'none' }}>
      <span className="card-title"><span className="dot9" />{title}</span>
      <button className={`pill-btn${action === 'Cancel' ? ' grey' : ''}`} onClick={onClose}>{action}</button>
    </div>
  );
}

export function EmergencySheet({ profile, onClose }: { profile: Profile | null; onClose: () => void }) {
  const plan = profile?.rescue_plan;
  const call = plan?.call?.length ? plan.call : ['999'];
  const they = profile?.role === 'carer' || !profile ? 'her' : 'you';
  return (
    <>
      <SheetHead title="Emergency plan" onClose={onClose} />
      <div className="scr" style={{ flex: 1, overflowY: 'auto', padding: '0 16px 30px', display: 'flex', flexDirection: 'column', gap: 12 }}>
        <div className="card" style={{ border: '2px solid var(--high)', display: 'flex', flexDirection: 'column', gap: 12 }}>
          <ol style={{ margin: 0, paddingLeft: 22, fontSize: 16.5, lineHeight: 1.45, display: 'flex', flexDirection: 'column', gap: 8 }}>
            <li>Note the time it started. Keep {they === 'her' ? 'her' : 'yourself'} safe; nothing in the mouth.</li>
            <li><b>Call {call.join(' or ')}</b> if a convulsive seizure passes {plan?.emergency_minutes_convulsive ?? 5} minutes, any seizure passes {plan?.emergency_minutes_other ?? 10} minutes or is longer than usual, a second one starts before recovery, breathing is affected, or there is injury or water.</li>
            {plan?.rescue_drug && <li>Rescue medicine: <b>{plan.rescue_drug} {plan.rescue_dose_mg ?? ''} mg</b>{plan.notes ? `. ${plan.notes}` : ''}</li>}
            <li>Afterwards: recovery position, stay until fully recovered, then log it.</li>
          </ol>
          <a href={`tel:${call[0]}`} style={{ height: 56, borderRadius: 28, background: 'var(--high-text)', color: '#FFFFFF', fontSize: 18, fontWeight: 650, display: 'flex', alignItems: 'center', justifyContent: 'center', textDecoration: 'none' }}>Call {call[0]}</a>
        </div>
        <div className="muted" style={{ fontSize: 12.5, padding: '0 6px' }}>This app is a diary aid, not a medical device, and does not detect or predict seizures.</div>
      </div>
    </>
  );
}

export function MedicinesSheet({ profile, onClose }: { profile: Profile | null; onClose: () => void }) {
  return (
    <>
      <SheetHead title="Medicines" onClose={onClose} />
      <div className="scr" style={{ flex: 1, overflowY: 'auto', padding: '0 16px 30px' }}>
        <div className="group" style={{ margin: 0 }}>
          {(profile?.medications ?? []).map((m, i) => (
            <div key={i} className="lrow" style={{ cursor: 'default' }}>
              <span className="ico" style={{ background: 'var(--blue-soft)', color: 'var(--blue)' }}><Icon d={IC.pill} /></span>
              <span className="txt"><span className="t1">{m.drug[0].toUpperCase() + m.drug.slice(1)} {m.dose_mg} mg</span><span className="t2">{m.as_needed ? 'Rescue, as needed' : m.times.join(', ')}</span></span>
            </div>
          ))}
        </div>
        <div className="muted" style={{ fontSize: 12.5, padding: '10px 6px' }}>Doses taken or missed are picked up when you talk to the assistant. The app never gives dosing advice.</div>
      </div>
    </>
  );
}

export function PrivacySheet({ onClose }: { onClose: () => void }) {
  return (
    <>
      <SheetHead title="What the assistant sees" onClose={onClose} />
      <div className="scr" style={{ flex: 1, overflowY: 'auto', padding: '0 16px 30px' }}>
        <div className="card" style={{ fontSize: 15, lineHeight: 1.5, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <span>Names in notes are replaced with role words and the NHS number is removed before anything is stored or sent to Gemini.</span>
          <span>The voice assistant hears the conversation and sees the medicine list and the triggers being tested, so it can ask the right question. It never sees the full diary.</span>
          <span>Every number on screen (risk, trends, trigger verdicts) is worked out by the app’s own code from the diary. Gemini words it; it never decides it.</span>
          <span className="muted" style={{ fontSize: 13 }}>Paid Gemini API tier only. Research prototype.</span>
        </div>
      </div>
    </>
  );
}
