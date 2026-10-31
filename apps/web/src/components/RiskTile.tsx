import type { RiskNow } from '@seizure/contracts';

const LABEL: Record<string, string> = { low: 'Low', medium: 'Medium', high: 'High' };

export function RiskTile({ risk, replayAt }: { risk: RiskNow | null; replayAt?: string }) {
  if (!risk) return <div className="risk nodata"><div className="tier">Loading…</div></div>;
  const cls = risk.overnight_no_data ? 'nodata' : risk.tier;
  const when = replayAt ? new Date(replayAt).toLocaleString(undefined, { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : 'now';
  return (
    <section className={`risk ${cls}`} aria-live="polite">
      <div className="horizon">Risk {when} · next {risk.horizon_hours} hours{risk.learning_mode ? ' · learning your pattern' : ''}</div>
      <div className="tier">{risk.overnight_no_data ? 'No data while asleep' : LABEL[risk.tier]}</div>
      <ul>
        {risk.reasons.map((r) => <li key={r.factor}>{r.text}</li>)}
      </ul>
      <div className="foot">{risk.disclaimer}</div>
    </section>
  );
}
