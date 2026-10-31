// The carer-facing trigger catalogue from the design, mapped onto the contract: catalogue entries with a context tag
// write that tag; everything else (and "Your own") is stored in SeizureEvent.factors. Rung captions come from /triggers.
import type { ContextTag, SeizureEvent, TriggerRung, TriggerTest } from '@seizure/contracts';
import { IC } from './icons';

type Entry = { icon: string; tag?: ContextTag; when: string; rank: number; common?: boolean };

export const CAT: Record<string, Entry> = {
  'Hot shower': { icon: IC.shower, tag: 'shower_bath', when: 'Just before', rank: 10 },
  'Missed dose': { icon: IC.pill, when: 'Morning dose', rank: 600, common: true },
  'Poor sleep': { icon: IC.moon, when: 'Last night', rank: 900 },
  Period: { icon: IC.drop, tag: 'period', when: 'Today', rank: 1000 },
  Stress: { icon: IC.bolt, when: 'Today', rank: 990 },
  Travel: { icon: IC.train, tag: 'travel', when: 'Earlier', rank: 300 },
  'Late night': { icon: IC.clock, tag: 'late_night', when: 'Last night', rank: 890 },
  Tired: { icon: IC.zzz, when: 'This morning', rank: 420 },
  Alcohol: { icon: IC.glass, when: 'Last night', rank: 880, common: true },
  Unwell: { icon: IC.thermo, tag: 'unwell', when: 'Today', rank: 980 },
  'Skipped meal': { icon: IC.fork, tag: 'hungry', when: 'Lunch', rank: 180 },
};
export const CAT_KEYS = Object.keys(CAT);

// Tags that arrive from imports or the extractor but have no catalogue chip.
const TAG_ONLY: Partial<Record<ContextTag, Entry & { label: string }>> = {
  hot: { label: 'Hot', icon: IC.sun, when: 'Just before', rank: 20 },
  cold: { label: 'Cold', icon: IC.snow, when: 'Just before', rank: 20 },
  exercise: { label: 'Exercise', icon: IC.run, when: 'Earlier', rank: 200 },
  upset: { label: 'Upset', icon: IC.bolt, when: 'Earlier', rank: 150 },
  school: { label: 'School', icon: IC.school, when: 'Today', rank: 700 },
  screen: { label: 'Screens', icon: IC.screen, when: 'Earlier', rank: 160 },
  other: { label: 'Other', icon: IC.dot, when: 'Before', rank: 5 },
};

export function tagLabel(tag: ContextTag): string {
  const hit = Object.entries(CAT).find(([, e]) => e.tag === tag);
  return hit ? hit[0] : (TAG_ONLY[tag]?.label ?? tag);
}

export function entryFor(label: string): Entry {
  if (CAT[label]) return CAT[label];
  const t = Object.values(TAG_ONLY).find((e) => e?.label === label);
  return t ?? { icon: IC.dot, when: 'Before', rank: 5 };
}

/** Everything that was going on before a seizure, as catalogue labels: context tags first, then free-text factors. */
export function factorLabels(e: SeizureEvent): string[] {
  const out: string[] = [];
  (e.context_tags ?? []).forEach((t) => { const l = tagLabel(t); if (!out.includes(l)) out.push(l); });
  (e.factors ?? []).forEach((f) => { if (!out.includes(f)) out.push(f); });
  return out;
}

/** The event patch that adds or removes one label, writing the tag when the catalogue has one. */
export function toggleFactor(e: SeizureEvent, label: string): Pick<SeizureEvent, 'context_tags' | 'factors'> {
  const has = factorLabels(e).includes(label);
  const tag = CAT[label]?.tag ?? (Object.entries(TAG_ONLY).find(([, v]) => v?.label === label)?.[0] as ContextTag | undefined);
  let tags = [...(e.context_tags ?? [])];
  let factors = [...(e.factors ?? [])];
  if (has) { tags = tags.filter((t) => t !== tag); factors = factors.filter((f) => f !== label); }
  else if (tag) tags.push(tag);
  else factors.push(label);
  return { context_tags: tags, factors };
}

export const RUNG_LABEL: Record<TriggerRung, string> = { supported: 'Supported', emerging: 'Emerging', watching: 'Watching', not_seen_so_far: 'Not seen so far', unlikely: 'Unlikely' };
export const RUNG_COLORS: Record<TriggerRung, [string, string]> = {
  supported: ['var(--rung-supported-bg)', 'var(--rung-supported-fg)'],
  emerging: ['var(--rung-emerging-bg)', 'var(--rung-emerging-fg)'],
  watching: ['var(--rung-watching-bg)', 'var(--rung-watching-fg)'],
  not_seen_so_far: ['var(--rung-watching-bg)', 'var(--rung-watching-fg)'],
  unlikely: ['var(--rung-unlikely-bg)', 'var(--rung-unlikely-fg)'],
};

/** The trigger test for a catalogue label, matched by context tag or by name. */
export function testFor(label: string, triggers: TriggerTest[]): TriggerTest | undefined {
  const l = label.toLowerCase();
  const words = l.split(' ');
  return triggers.find((t) => t.trigger.toLowerCase() === l)
    ?? triggers.find((t) => t.trigger.toLowerCase().includes(l) || words.every((w) => t.trigger.toLowerCase().includes(w)))
    ?? (l === 'hot shower' ? triggers.find((t) => /shower|bath/i.test(t.trigger)) : undefined);
}

/** "Supported · 2.1× for her" style caption with its colour; always a rung and, when there is one, a number. */
export function statFor(label: string, triggers: TriggerTest[], her = 'her'): { text: string; color: string } {
  const t = testFor(label, triggers);
  if (t) {
    const r = t.ratio != null ? `${t.ratio.toFixed(1)}×` : '';
    const text = t.rung === 'supported' ? `Supported · ${r} for ${her}`
      : t.rung === 'emerging' ? `Emerging · ${r} so far`
      : t.rung === 'watching' ? `Watching${t.units_to_next_verdict ? ` · ${t.units_to_next_verdict} more days to go` : ''}`
      : `${RUNG_LABEL[t.rung]}${r ? ` · ${r}` : ''}`;
    const color = t.rung === 'supported' ? 'var(--blue)' : t.rung === 'emerging' ? 'var(--stat-emerging)' : 'var(--ink-3)';
    return { text, color };
  }
  if (CAT[label]?.common) return { text: 'Common trigger · Often a trigger', color: 'var(--ink-2)' };
  return { text: CAT[label] || entryFor(label).rank !== 5 ? 'Watching' : 'Your own', color: 'var(--ink-3)' };
}
