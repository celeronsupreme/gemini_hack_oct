// App state: one zustand store. Home is always mounted; everything else is a pushed screen or a sheet over it,
// as in the design reference. The API client is the only thing that writes data.
import { create } from 'zustand';
import type { BaselineStats, HourlyStats, MonthlyStats, Profile, RiskNow, SeizureEvent, TriggerTest } from '@seizure/contracts';
import { api } from '@/api/client';
import { daysAgo, durTxt, hhmm, startOfDay } from '@/ui/format';

export type Screen = 'home' | 'trends' | 'account' | 'timer' | 'talk';
export type Sheet = null | { kind: 'detail'; id: string } | { kind: 'export'; fmt: 'pdf' | 'csv' } | { kind: 'emergency' } | { kind: 'medicines' } | { kind: 'privacy' };

type Timer = { t0: number; stoppedAt: number | null; eventId: string | null; pending: Promise<SeizureEvent | null> | null };

type State = {
  screen: Screen;
  sheet: Sheet;
  toast: string | null;
  profile: Profile | null;
  risk: RiskNow | null;
  today: SeizureEvent[];
  year: SeizureEvent[]; // last 365 days, for the Home counters and Trends' last 7 days
  triggers: TriggerTest[];
  hourly: HourlyStats | null;
  monthly: MonthlyStats | null;
  baseline: BaselineStats | null;
  timer: Timer | null;
  error: string | null;
  go: (s: Screen) => void;
  open: (s: Sheet) => void;
  flash: (msg: string) => void;
  loadHome: () => Promise<void>;
  loadTrends: () => Promise<void>;
  loadTriggers: () => Promise<void>;
  startTimer: () => void;
  stopTimer: () => Promise<void>;
  timedEventId: () => Promise<string | null>;
  discardTimer: () => Promise<void>;
  finishTimer: (msg?: string) => Promise<void>;
  patchEvent: (id: string, patch: Partial<SeizureEvent>) => Promise<void>;
  deleteEvent: (id: string) => Promise<void>;
};

let toastTimer: ReturnType<typeof setTimeout> | undefined;

export const useStore = create<State>((set, get) => ({
  screen: 'home', sheet: null, toast: null, profile: null, risk: null, today: [], year: [], triggers: [], hourly: null, monthly: null, baseline: null, timer: null, error: null,

  go: (screen) => set({ screen }),
  open: (sheet) => set({ sheet }),
  flash: (msg) => { clearTimeout(toastTimer); set({ toast: msg }); toastTimer = setTimeout(() => set({ toast: null }), 3200); },

  loadHome: async () => {
    try {
      const [profile, risk, today, year] = await Promise.all([api.profile(), api.riskNow(), api.events(startOfDay().toISOString(), undefined, 200), api.events(daysAgo(365).toISOString(), undefined, 5000)]);
      set({ profile, risk, today, year, error: null });
    } catch (e) { set({ error: String(e) }); }
    if (!get().triggers.length) void get().loadTriggers(); // rung captions (Lead-up) and Account's "N tested"
  },
  loadTrends: async () => {
    try {
      const [hourly, monthly, baseline] = await Promise.all([api.hourly(), api.monthly(), api.baseline()]);
      set({ hourly, monthly, baseline, error: null });
    } catch (e) { set({ error: String(e) }); }
    void get().loadTriggers();
  },
  loadTriggers: async () => {
    try { set({ triggers: await api.triggers() }); } catch (e) { set({ error: String(e) }); }
  },

  // The Seizure bar never waits for the network: the timer starts now, the tap event is written in the background.
  startTimer: () => {
    const pending = api.tap().then((ev) => { const t = get().timer; if (t && t.pending === pending) set({ timer: { ...t, eventId: ev.id ?? null } }); return ev; }).catch(() => null);
    set({ screen: 'timer', timer: { t0: Date.now(), stoppedAt: null, eventId: null, pending } });
  },
  stopTimer: async () => {
    const t = get().timer; if (!t || t.stoppedAt) return;
    const stoppedAt = Date.now();
    set({ timer: { ...t, stoppedAt } });
    const id = await get().timedEventId();
    if (id) await api.patchEvent(id, { duration_s: Math.max(1, Math.round((stoppedAt - t.t0) / 1000)), duration_estimated: false, still_going: false, recovered_at: new Date(stoppedAt).toISOString() }).catch(() => undefined);
  },
  timedEventId: async () => {
    const t = get().timer; if (!t) return null;
    if (t.eventId) return t.eventId;
    const ev = await t.pending; return ev?.id ?? null;
  },
  discardTimer: async () => {
    const id = await get().timedEventId();
    set({ timer: null, screen: 'home' });
    if (id) await api.deleteEvent(id).catch(() => undefined);
    void get().loadHome();
  },
  finishTimer: async (msg) => {
    const t = get().timer;
    if (t && !t.stoppedAt) await get().stopTimer();
    const tt = get().timer;
    set({ timer: null, screen: 'home' });
    if (tt) get().flash(msg ?? `Saved · ${hhmm(new Date(tt.t0))} · ${durTxt(((tt.stoppedAt ?? Date.now()) - tt.t0) / 1000)}`);
    await get().loadHome();
  },

  patchEvent: async (id, patch) => {
    // Optimistic: the sheet edits in place, the server catches up.
    const swap = (list: SeizureEvent[]) => list.map((e) => (e.id === id ? { ...e, ...patch } : e));
    set({ today: swap(get().today), year: swap(get().year) });
    try { await api.patchEvent(id, patch); } catch (e) { set({ error: String(e) }); }
    void api.riskNow().then((risk) => set({ risk })).catch(() => undefined);
  },
  deleteEvent: async (id) => {
    set({ sheet: null, today: get().today.filter((e) => e.id !== id), year: get().year.filter((e) => e.id !== id) });
    await api.deleteEvent(id).catch((e) => set({ error: String(e) }));
    await get().loadHome();
  },
}));

/** "her" for a carer's diary, "your" for the person themselves; the design is written for a carer. */
export const herOf = (p: Profile | null) => (p?.role === 'carer' || !p ? 'her' : 'your');
export const sheOf = (p: Profile | null) => (p?.role === 'carer' || !p ? 'she' : 'you');
