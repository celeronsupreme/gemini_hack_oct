import { NavLink } from 'react-router-dom';
const items = [['/', '⌂', 'Home'], ['/log', '🎤', 'Log'], ['/timeline', '◔', 'Patterns'], ['/triggers', '⚗', 'Triggers'], ['/report', '▤', 'Report']] as const;
export function Nav() {
  return (
    <nav className="nav">
      {items.map(([to, ico, label]) => <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => (isActive ? 'active' : '')}><span className="ico">{ico}</span>{label}</NavLink>)}
    </nav>
  );
}
