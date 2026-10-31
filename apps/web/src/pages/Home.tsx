import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useStore } from '@/state/store';
import { RiskTile } from '@/components/RiskTile';
import { TapButton } from '@/components/TapButton';

const TYPE_WORDS: Record<string, string> = { aware: 'aware', staring: 'staring', impaired_awareness: 'not aware', convulsive: 'convulsive', drop: 'drop', jerk: 'jerk', unsure: 'unsure' };

export function Home() {
  const { risk, riskAt, baseline, todayEvents, profile, error, loadHome } = useStore();
  useEffect(() => { void loadHome(); const id = setInterval(() => void loadHome(), 60_000); return () => clearInterval(id); }, [loadHome]);
  return (
    <div className="screen">
      <div className="row">
        <h1 className="grow">{profile?.display_name ? `${profile.display_name}'s diary` : 'Seizure diary'}</h1>
        <Link to="/emergency" className="btn danger" style={{ minHeight: 44, padding: '0 14px' }}>Emergency</Link>
      </div>
      {error && <div className="error">{error}</div>}
      <TapButton />
      <RiskTile risk={risk} replayAt={riskAt} />
      {baseline && (
        <div className="card">
          <div className="row"><b className="grow">This week: {baseline.this_week} seizures</b><span className="chip">{baseline.this_week_verdict}</span></div>
          <div className="muted">Your usual week over the last {baseline.window_days} days: {baseline.weekly_p25}–{baseline.weekly_p75} (median {baseline.weekly_median}); {baseline.pct_days_with_seizure}% of days have one.</div>
        </div>
      )}
      <h2>Today</h2>
      <div className="list">
        {todayEvents.length === 0 && <div className="muted">Nothing logged today.</div>}
        {todayEvents.slice().reverse().map((e) => (
          <Link to={`/log?event=${e.id}`} key={e.id} className="item">
            <span className={`dot ${e.severity === 'severe' ? 'severe' : ''}`} />
            <span className="time">{new Date(e.start_time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            <span className="grow">{TYPE_WORDS[e.type]}{e.duration_s ? ` · ${e.duration_s}s` : e.still_going ? ' · still going' : ''}{e.context_tags?.length ? ` · ${e.context_tags.join(', ')}` : ''}</span>
            <span className="muted">{e.source}</span>
          </Link>
        ))}
      </div>
      <Link to="/log" className="btn">Tell me about one by voice</Link>
    </div>
  );
}
