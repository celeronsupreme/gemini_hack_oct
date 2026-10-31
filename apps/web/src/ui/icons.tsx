// Stroke icons from the design reference (24-unit paths, 1.9 stroke, round caps). No emoji anywhere in the app.
export const IC = {
  shower: 'M4 21V8a4 4 0 0 1 4-4h1a4 4 0 0 1 4 4 M9 8h8 M10 12v1.5 M13.5 12v1.5 M17 12v1.5 M11.5 16v1.5 M15 16v1.5',
  drop: 'M12 3.5s6 6.2 6 10.5a6 6 0 0 1-12 0c0-4.3 6-10.5 6-10.5z',
  moon: 'M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z',
  pill: 'M10.5 20.5a5 5 0 0 1-7-7l6-6a5 5 0 0 1 7 7z M7 10l7 7',
  train: 'M7 3h10a2 2 0 0 1 2 2v9a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3V5a2 2 0 0 1 2-2z M5 10h14 M9 14h.01 M15 14h.01 M8 17l-2 4 M16 17l2 4',
  clock: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z M12 7v5l3 2',
  bolt: 'M13 2 4 14h7l-1 8 9-12h-7z',
  glass: 'M7 3h10l-1 7a4 4 0 0 1-8 0z M12 14v7 M8 21h8',
  zzz: 'M4 6h6l-6 7h6 M13 12h6l-6 7h6',
  thermo: 'M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0z',
  fork: 'M6 3v7a2 2 0 0 0 4 0V3 M8 12v9 M17 21V3c-2 1.5-3 4-3 7h3',
  dot: 'M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8z',
  seizure: 'M3 12h4l2-5 3 10 2-5h7',
  doc: 'M7 3h7l5 5v13H7z M14 3v5h5 M10 13h6 M10 17h6',
  download: 'M12 4v11 M7 10l5 5 5-5 M5 20h14',
  link: 'M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1 M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1',
  cross: 'M9 3h6v6h6v6h-6v6H9v-6H3V9h6z',
  flask: 'M9 3h6 M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3',
  shield: 'M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z',
  trash: 'M4 7h16 M9 7V4h6v3 M6 7l1 13h10l1-13',
  check: 'M5 12.5l4.5 4.5L19 7',
  x: 'M6 6l12 12 M18 6L6 18',
  plus: 'M12 5v14 M5 12h14',
  mic: 'M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3z M5 11a7 7 0 0 0 14 0 M12 18v3',
  file: 'M7 3h7l5 5v13H7z M14 3v5h5',
  run: 'M13 4a1.5 1.5 0 1 0 0 .01 M9 21l3-6 3 3v5 M6 12l3-4 4 1 3 4 3 1',
  heart: 'M12 20s-7-4.5-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.5-7 10-7 10z',
  school: 'M3 9l9-5 9 5-9 5z M7 11v5c0 1.5 2.5 3 5 3s5-1.5 5-3v-5',
  sun: 'M12 8a4 4 0 1 1 0 8 4 4 0 0 1 0-8z M12 2v2 M12 20v2 M4.9 4.9l1.4 1.4 M17.7 17.7l1.4 1.4 M2 12h2 M20 12h2 M4.9 19.1l1.4-1.4 M17.7 6.3l1.4-1.4',
  snow: 'M12 2v20 M4 7l16 10 M20 7L4 17',
  screen: 'M4 5h16v11H4z M9 20h6 M12 16v4',
} as const;
export type IconName = keyof typeof IC;

export function Icon({ d, size = 19, stroke = 1.9, style }: { d: string; size?: number; stroke?: number; style?: React.CSSProperties }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={style}>
      <path d={d} />
    </svg>
  );
}
