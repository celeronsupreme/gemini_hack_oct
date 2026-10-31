// Hand-rolled SVG charts: no chart library, so Claude Design can restyle freely and the bundle stays small.
import type { HourlyStats, MonthlyStats } from '@seizure/contracts';

export function HourHistogram({ data, highlightHour }: { data: HourlyStats; highlightHour?: number }) {
  const W = 480, H = 170, pad = { l: 28, r: 8, t: 10, b: 26 };
  const max = Math.max(1, ...data.by_hour.map((h) => h.all));
  const bw = (W - pad.l - pad.r) / 24;
  const y = (v: number) => pad.t + (H - pad.t - pad.b) * (1 - v / max);
  const doseHours = data.scheduled_dose_times.map((t) => parseInt(t.split(':')[0], 10));
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Seizures by hour of day">
      {data.by_hour.map((h) => {
        const x = pad.l + h.hour * bw;
        const mildH = y(h.all - h.severe), sevTop = y(h.all);
        const hot = highlightHour !== undefined && h.hour >= highlightHour && h.hour < highlightHour + 3;
        return (
          <g key={h.hour} opacity={highlightHour === undefined || hot ? 1 : 0.45}>
            <rect x={x + 1} y={sevTop} width={bw - 2} height={mildH - sevTop} fill="var(--high)" rx="2" />
            <rect x={x + 1} y={mildH} width={bw - 2} height={H - pad.b - mildH} fill="var(--accent)" rx="2" />
            {h.hour % 3 === 0 && <text x={x + bw / 2} y={H - 8} fontSize="10" textAnchor="middle" fill="var(--ink-3)">{String(h.hour).padStart(2, '0')}</text>}
          </g>
        );
      })}
      {doseHours.map((hh, i) => (
        <g key={i}>
          <line x1={pad.l + hh * bw} x2={pad.l + hh * bw} y1={pad.t} y2={H - pad.b} stroke="var(--ink-3)" strokeDasharray="3 3" />
          <text x={pad.l + hh * bw + 3} y={pad.t + 10} fontSize="9" fill="var(--ink-3)">dose</text>
        </g>
      ))}
      <text x={4} y={pad.t + 10} fontSize="10" fill="var(--ink-3)">{max}</text>
    </svg>
  );
}

export function MonthlyBars({ data, months = 36 }: { data: MonthlyStats; months?: number }) {
  const rows = data.months.slice(-months);
  const W = 480, H = 190, pad = { l: 26, r: 8, t: 30, b: 24 };
  const max = Math.max(1, ...rows.map((m) => m.all));
  const bw = (W - pad.l - pad.r) / Math.max(rows.length, 1);
  const y = (v: number) => pad.t + (H - pad.t - pad.b) * (1 - v / max);
  const first = rows[0]?.month, last = rows[rows.length - 1]?.month;
  const changes = data.medication_changes.filter((c) => first && last && c.date.slice(0, 7) >= first && c.date.slice(0, 7) <= last && (c.verdict.includes('rise') || c.verdict.includes('fall') || c.action === 'start' || c.action === 'stop'));
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Seizures per month">
      {rows.map((m, i) => {
        const x = pad.l + i * bw;
        return (
          <g key={m.month}>
            <rect x={x + 1} y={y(m.all)} width={Math.max(bw - 2, 1)} height={H - pad.b - y(m.all)} fill="var(--accent)" rx="1.5" />
            <rect x={x + 1} y={y(m.severe)} width={Math.max(bw - 2, 1)} height={H - pad.b - y(m.severe)} fill="var(--high)" rx="1.5" />
            {m.month.endsWith('-01') && <text x={x + bw / 2} y={H - 8} fontSize="10" textAnchor="middle" fill="var(--ink-3)">{m.month.slice(0, 4)}</text>}
          </g>
        );
      })}
      {changes.map((c, i) => {
        const idx = rows.findIndex((m) => m.month === c.date.slice(0, 7));
        if (idx < 0) return null;
        const x = pad.l + idx * bw + bw / 2;
        return (
          <g key={i}>
            <line x1={x} x2={x} y1={pad.t - 4} y2={H - pad.b} stroke="var(--ink-2)" strokeDasharray="2 3" />
            <text x={x + 3} y={pad.t - 8 - (i % 2) * 10} fontSize="9" fill="var(--ink-2)">{c.drug.split(' ')[0]} {c.action}</text>
          </g>
        );
      })}
      <text x={4} y={pad.t + 8} fontSize="10" fill="var(--ink-3)">{max}</text>
    </svg>
  );
}
