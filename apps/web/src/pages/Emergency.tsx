// Always one tap away. Wording follows the NHS first-aid page; the rescue plan comes from the profile.
import { useStore } from '@/state/store';

export function Emergency() {
  const profile = useStore((s) => s.profile);
  const plan = profile?.rescue_plan;
  const call = plan?.call?.length ? plan.call : ['999'];
  return (
    <div className="screen">
      <div className="card emergency">
        <h1>Emergency plan</h1>
        <ol>
          <li>Note the time it started. Keep them safe; nothing in the mouth.</li>
          <li><b>Call {call.join(' or ')}</b> if a convulsive seizure passes {plan?.emergency_minutes_convulsive ?? 5} minutes, any seizure passes {plan?.emergency_minutes_other ?? 10} minutes or is longer than usual, a second one starts before recovery, breathing is affected, or there is injury or water.</li>
          {plan?.rescue_drug && <li>Rescue medicine: <b>{plan.rescue_drug} {plan.rescue_dose_mg ?? ''} mg</b>{plan.notes ? ` — ${plan.notes}` : ''}</li>}
          <li>Afterwards: recovery position, stay with them until fully recovered, log it.</li>
        </ol>
        <a className="btn danger" href={`tel:${call[0]}`} style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>Call {call[0]}</a>
      </div>
      <div className="muted">This app is a diary aid, not a medical device, and does not detect or predict seizures.</div>
    </div>
  );
}
