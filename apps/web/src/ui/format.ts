// Small formatting helpers shared by every screen.
const pad = (n: number) => String(n).padStart(2, '0');

export const hhmm = (iso: string | Date) => { const d = new Date(iso); return `${pad(d.getHours())}:${pad(d.getMinutes())}`; };
export const minsOfDay = (iso: string | Date) => { const d = new Date(iso); return d.getHours() * 60 + d.getMinutes(); };
export const mmss = (s: number) => `${pad(Math.floor(s / 60))}:${pad(Math.floor(s % 60))}`;
export const durTxt = (s?: number | null) => {
  if (s == null) return '';
  s = Math.round(s); const m = Math.floor(s / 60), r = s % 60;
  return m ? `${m}m ${pad(r)}s` : `${r}s`;
};
/** Parse "1m 10s", "70s", "1:10" or "90" back to seconds; null when unreadable. */
export const parseDur = (v: string): number | null => {
  const t = v.trim().toLowerCase();
  let m = /^(\d+)\s*m(?:in)?\s*(\d+)?\s*s?$/.exec(t); if (m) return +m[1] * 60 + (m[2] ? +m[2] : 0);
  m = /^(\d+):(\d{1,2})$/.exec(t); if (m) return +m[1] * 60 + +m[2];
  m = /^(\d+)\s*s?(?:ec)?$/.exec(t); if (m) return +m[1];
  return null;
};
export const h12 = (h: number) => (h === 0 ? '12 am' : h < 12 ? `${h} am` : h === 12 ? '12 pm' : `${h - 12} pm`);
export const startOfDay = (d = new Date()) => { const x = new Date(d); x.setHours(0, 0, 0, 0); return x; };
export const daysAgo = (n: number) => { const x = startOfDay(); x.setDate(x.getDate() - n); return x; };
export const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
export const headerDate = (d = new Date()) => d.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' }).replace(',', '').toUpperCase();
export const MONTH = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
export const MON = MONTH.map((m) => m.slice(0, 3));
