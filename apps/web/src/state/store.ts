// App state: one small zustand store. Screens read from here; the API client is the only thing that writes.
import { create } from 'zustand';
import type { BaselineStats, HourlyStats, MonthlyStats, Profile, RiskNow, SeizureEvent, TriggerTest } from '@seizure/contracts';
import { api } from '@/api/client';

export type TimerState = { eventId: string | null; startedAt: number | null };

type State = {
  profile: Profile | null;
  risk: RiskNow | null;
  riskAt: string | undefined; // undefined = now; an ISO string when the timeline scrubber is replaying
  hourly: HourlyStats | null;
  monthly: MonthlyStats | null;
  baseline: BaselineStats | null;
  todayEvents: SeizureEvent[];
  triggers: TriggerTest[];
  timer: TimerState;
  error: string | null;
  loadHome: () => Promise<void>;
  loadTimeline: () => Promise<void>;
  loadTriggers: () => Promise<void>;
  setRiskAt: (at?: string) => Promise<void>;
  tap: () => Promise<SeizureEvent>;
  stopTimer: () => Promise<SeizureEvent | null>;
};

function startOfToday(): string {
  const d = new Date(); d.setHours(0, 0, 0, 0); return d.toISOString();
}

export const useStore = create<State>((set, get) => ({
  profile: null, risk: null, riskAt: undefined, hourly: null, monthly: null, baseline: null, todayEvents: [], triggers: [],
  timer: { eventId: null, startedAt: null }, error: null,

  loadHome: async () => {
    try {
      const [profile, risk, baseline, todayEvents] = await Promise.all([api.profile(), api.riskNow(get().riskAt), api.baseline(get().riskAt), api.events(startOfToday())]);
      set({ profile, risk, baseline, todayEvents, error: null });
    } catch (e) { set({ error: String(e) }); }
  },
  loadTimeline: async () => {
    try {
      const [hourly, monthly] = await Promise.all([api.hourly(get().riskAt), api.monthly()]);
      set({ hourly, monthly, error: null });
    } catch (e) { set({ error: String(e) }); }
  },
  loadTriggers: async () => {
    try { set({ triggers: await api.triggers(), error: null }); } catch (e) { set({ error: String(e) }); }
  },
  setRiskAt: async (at) => {
    set({ riskAt: at });
    try { set({ risk: await api.riskNow(at), baseline: await api.baseline(at) }); } catch (e) { set({ error: String(e) }); }
  },
  tap: async () => {
    const ev = await api.tap();
    set({ timer: { eventId: ev.id ?? null, startedAt: Date.now() } });
    await get().loadHome();
    return ev;
  },
  stopTimer: async () => {
    const { timer } = get();
    if (!timer.eventId || !timer.startedAt) return null;
    const duration_s = Math.max(1, Math.round((Date.now() - timer.startedAt) / 1000));
    const ev = await api.patchEvent(timer.eventId, { duration_s, still_going: false, recovered_at: new Date().toISOString() });
    set({ timer: { eventId: null, startedAt: null } });
    await get().loadHome();
    return ev;
  },
}));
