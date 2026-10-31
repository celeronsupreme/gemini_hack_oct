// Typed API client. Every read can be served from fixtures with VITE_USE_MOCK=1 (the API then returns
// packages/contracts/fixtures/<name>.json), so the UI never waits on the backend.
import type {
  AnalysisAnswer, BaselineStats, CheckIn, ClinicReport, DiaryEntryBatch, Dose, HourlyStats, ImportPreview, LiveToken,
  MonthlyStats, Profile, RiskNow, SeizureEvent, TriggerDefinition, TriggerTest,
} from '@seizure/contracts';

const BASE = import.meta.env.VITE_API_BASE || '/api';
const MOCK = import.meta.env.VITE_USE_MOCK === '1';

function qs(params: Record<string, string | number | undefined>): string {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => { if (v !== undefined && v !== '') p.set(k, String(v)); });
  if (MOCK) p.set('mock', '1');
  const s = p.toString();
  return s ? `?${s}` : '';
}

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) }, ...init });
  if (!res.ok) throw new Error(`${init?.method || 'GET'} ${path} → ${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<{ ok: boolean; gemini: boolean; counts: Record<string, number> }>('/health'),
  profile: () => req<Profile>(`/profile${qs({})}`),
  saveProfile: (p: Profile) => req<Profile>('/profile', { method: 'PUT', body: JSON.stringify(p) }),

  events: (from?: string, to?: string, limit = 500) => req<SeizureEvent[]>(`/events${qs({ from, to, limit })}`),
  tap: () => req<SeizureEvent>('/events/tap', { method: 'POST', body: '{}' }),
  patchEvent: (id: string, patch: Partial<SeizureEvent>) => req<SeizureEvent>(`/events/${id}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  addDose: (d: Dose) => req<Dose>('/doses', { method: 'POST', body: JSON.stringify(d) }),
  addCheckIn: (c: CheckIn) => req<CheckIn>('/checkins', { method: 'POST', body: JSON.stringify(c) }),

  riskNow: (at?: string) => req<RiskNow>(`/risk/now${qs({ at })}`),
  hourly: (at?: string, windowDays?: number) => req<HourlyStats>(`/stats/hourly${qs({ at, window_days: windowDays })}`),
  monthly: () => req<MonthlyStats>(`/stats/monthly${qs({})}`),
  baseline: (at?: string) => req<BaselineStats>(`/stats/baseline${qs({ at })}`),

  triggers: () => req<TriggerTest[]>(`/triggers${qs({})}`),
  addTrigger: (d: TriggerDefinition) => req<TriggerTest>('/triggers', { method: 'POST', body: JSON.stringify(d) }),
  retestTriggers: () => req<TriggerTest[]>('/triggers/test', { method: 'POST', body: '{}' }),
  archiveTrigger: (id: string) => req<{ ok: boolean }>(`/triggers/${id}/archive`, { method: 'POST', body: '{}' }),

  clinicReport: (window = 90, at?: string) => req<ClinicReport>(`/report/clinic${qs({ window, at })}`),
  saveQuestions: (questions: string[]) => req<{ ok: boolean }>('/report/questions', { method: 'PUT', body: JSON.stringify({ questions }) }),

  liveToken: () => req<LiveToken>(`/live/token${qs({})}`, { method: 'POST', body: '{}' }),
  liveTool: (call: { id: string; name: string; args: Record<string, unknown> }) => req<{ id: string; name: string; response: Record<string, unknown> }>('/live/tool', { method: 'POST', body: JSON.stringify(call) }),
  extract: (transcript: string) => req<DiaryEntryBatch>(`/transcripts/extract${qs({})}`, { method: 'POST', body: JSON.stringify({ transcript }) }),
  commit: (batch: DiaryEntryBatch) => req<SeizureEvent[]>('/transcripts/commit', { method: 'POST', body: JSON.stringify(batch) }),

  ask: (question: string) => req<AnalysisAnswer>(`/analysis/ask${qs({})}`, { method: 'POST', body: JSON.stringify({ question }) }),

  importPreview: async (file: File): Promise<ImportPreview> => {
    const fd = new FormData(); fd.append('file', file);
    const res = await fetch(`${BASE}/import/preview${qs({})}`, { method: 'POST', body: fd });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
  importCommit: (job_id: string, label_mapping: Record<string, string>, replace: boolean) => req<{ imported: number }>('/import/commit', { method: 'POST', body: JSON.stringify({ job_id, label_mapping, replace }) }),
};

export const isMock = MOCK;
