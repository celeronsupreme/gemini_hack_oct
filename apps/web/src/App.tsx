// One phone-width stage, no tab bar: Home is always there; Trends and Account push over it; the timer and the
// assistant fill it with blue; details, export and the account sheets rise from the bottom.
import { useEffect, useRef } from 'react';
import { useStore, type Sheet } from '@/state/store';
import { Home } from '@/screens/Home';
import { Trends } from '@/screens/Trends';
import { Account, EmergencySheet, MedicinesSheet, PrivacySheet } from '@/screens/Account';
import { BlueFill, Timer } from '@/screens/Timer';
import { Talk } from '@/screens/Talk';
import { DetailsSheet } from '@/screens/Details';
import { ExportSheet } from '@/screens/Export';
import { Icon, IC } from '@/ui/icons';

export default function App() {
  const { sheet, open, toast, profile, error } = useStore();
  // Keep the last sheet rendered while it slides away.
  const last = useRef<Sheet>(null);
  if (sheet) last.current = sheet;
  const shown = sheet ?? last.current;
  const close = () => open(null);
  useEffect(() => { if (error) console.warn(error); }, [error]);
  // Deep links for demos and screenshots: ?screen=trends|account, ?sheet=export|csv|emergency|medicines|privacy|latest.
  useEffect(() => {
    const p = new URLSearchParams(location.search), s = p.get('screen'), sh = p.get('sheet');
    if (p.has('frame')) { document.body.classList.add('frame'); const h = Number(p.get('frame')); if (h > 100) document.body.style.setProperty('--frame-h', `${h}px`); } // pin a 390px stage left (optionally ?frame=<height>), for screenshots
    if (s === 'trends' || s === 'account') useStore.getState().go(s);
    if (sh === 'export' || sh === 'csv') open({ kind: 'export', fmt: sh === 'csv' ? 'csv' : 'pdf' });
    if (sh === 'emergency' || sh === 'medicines' || sh === 'privacy') open({ kind: sh });
    if (sh === 'latest') void useStore.getState().loadHome().then(() => { const t = useStore.getState().today; const y = useStore.getState().year; const e = t[t.length - 1] ?? y[y.length - 1]; if (e?.id) open({ kind: 'detail', id: e.id }); });
  }, [open]);
  return (
    <div className="stage">
      <Home />
      <Trends />
      <Account />
      <BlueFill />
      <Timer />
      <Talk />
      <div className="sheet-wrap" style={{ zIndex: 40, pointerEvents: sheet ? 'auto' : 'none' }}>
        <div className="sheet-scrim" onClick={close} style={{ opacity: sheet ? 1 : 0 }} />
        <div className="sheet" style={{ transform: sheet ? 'none' : 'translateY(102%)' }}>
          <div className="handle"><span /></div>
          {shown?.kind === 'detail' && <DetailsSheet id={shown.id} onClose={close} />}
          {shown?.kind === 'export' && <ExportSheet key={`${shown.fmt}-${!!sheet}`} fmt={shown.fmt} onClose={close} />}
          {shown?.kind === 'emergency' && <EmergencySheet profile={profile} onClose={close} />}
          {shown?.kind === 'medicines' && <MedicinesSheet profile={profile} onClose={close} />}
          {shown?.kind === 'privacy' && <PrivacySheet onClose={close} />}
        </div>
      </div>
      <div className="toast" style={{ opacity: toast ? 1 : 0, transform: `translateY(${toast ? 0 : -14}px)` }}>
        <div><span className="tick"><Icon d={IC.check} size={12} stroke={3} /></span>{toast ?? ''}</div>
      </div>
    </div>
  );
}
