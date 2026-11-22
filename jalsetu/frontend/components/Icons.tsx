// Inline line icons. Stroke/fill use currentColor so CSS controls colour.
type P = React.SVGProps<SVGSVGElement>;
const S = (p: P) => ({ width: 24, height: 24, viewBox: "0 0 24 24", "aria-hidden": true as const, ...p });
const line = { fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };

export const Icon = {
  drop: (p: P) => (
    <svg {...S(p)}>
      <path d="M12 2.5S5.5 10 5.5 14.5a6.5 6.5 0 0 0 13 0C18.5 10 12 2.5 12 2.5Z" fill="currentColor" />
      <path d="M9 14.5a3 3 0 0 0 3 3" fill="none" stroke="#fff" strokeWidth="1.5" strokeLinecap="round" opacity=".85" />
    </svg>
  ),
  close: (p: P) => (
    <svg {...S(p)}>
      <path d="M6 6l12 12M18 6 6 18" {...line} strokeWidth={2} />
    </svg>
  ),
  chevL: (p: P) => (
    <svg {...S({ viewBox: "0 0 30 60", width: 30, height: 60, ...p })}>
      <path d="M26 2 4 30l22 28" {...line} strokeWidth={2.4} />
    </svg>
  ),
  chevR: (p: P) => (
    <svg {...S({ viewBox: "0 0 30 60", width: 30, height: 60, ...p })}>
      <path d="m4 2 22 28L4 58" {...line} strokeWidth={2.4} />
    </svg>
  ),
  chevDown: (p: P) => (
    <svg {...S(p)}>
      <path d="m6 9 6 6 6-6" {...line} strokeWidth={2} />
    </svg>
  ),
  phone: (p: P) => (
    <svg {...S(p)}>
      <path
        d="M6.6 3.5 8.9 3a1.2 1.2 0 0 1 1.3.7l1.2 2.9a1.2 1.2 0 0 1-.3 1.3L9.6 9.2a10 10 0 0 0 5.2 5.2l1.3-1.5a1.2 1.2 0 0 1 1.3-.3l2.9 1.2a1.2 1.2 0 0 1 .7 1.3l-.5 2.3a1.6 1.6 0 0 1-1.6 1.3C10.6 18.7 5.3 13.4 5.3 5.1a1.6 1.6 0 0 1 1.3-1.6Z"
        fill="currentColor"
      />
    </svg>
  ),
  phoneWaves: (p: P) => (
    <svg {...S({ viewBox: "0 0 32 32", ...p })}>
      <path
        d="M8.2 5.5 11 4.9a1.4 1.4 0 0 1 1.6.8l1.5 3.5a1.4 1.4 0 0 1-.4 1.6l-1.8 1.5a12 12 0 0 0 6.2 6.2l1.5-1.8a1.4 1.4 0 0 1 1.6-.4l3.5 1.5a1.4 1.4 0 0 1 .8 1.6l-.6 2.8a2 2 0 0 1-2 1.6C14 23.8 6.6 16.5 6.6 7.5a2 2 0 0 1 1.6-2Z"
        fill="currentColor"
      />
      <path d="M18.5 4.5a9 9 0 0 1 9 9M18.5 8.5a5 5 0 0 1 5 5" {...line} strokeWidth={2} />
    </svg>
  ),
  chat: (p: P) => (
    <svg {...S(p)}>
      <path d="M4 19.5 5.2 16A8 8 0 1 1 8.4 19z" {...line} strokeWidth={1.8} />
      <path d="M9.2 8.8c.2-.5.6-.5.9-.4l.8 1.6c.1.3 0 .5-.2.7l-.4.4a5 5 0 0 0 2.4 2.4l.4-.4c.2-.2.4-.3.7-.2l1.6.8c.1.3.1.7-.4.9-1 .6-2.6.2-4-1.2s-1.9-3-1.8-4.6Z" fill="currentColor" />
    </svg>
  ),
  pin: (p: P) => (
    <svg {...S(p)}>
      <path d="M12 21.5s-6.5-6.2-6.5-11.2a6.5 6.5 0 0 1 13 0c0 5-6.5 11.2-6.5 11.2Z" fill="currentColor" />
      <circle cx="12" cy="10.3" r="2.4" fill="#fff" />
    </svg>
  ),
  locate: (p: P) => (
    <svg {...S(p)}>
      <circle cx="12" cy="12" r="6.5" {...line} strokeWidth={1.8} />
      <circle cx="12" cy="12" r="2.4" fill="currentColor" />
      <path d="M12 2v3M12 19v3M2 12h3M19 12h3" {...line} strokeWidth={1.8} />
    </svg>
  ),
  zoom: (p: P) => (
    <svg {...S({ viewBox: "0 0 48 48", ...p })}>
      <circle cx="20" cy="20" r="14" fill="rgba(255,255,255,.75)" stroke="currentColor" strokeWidth="3.2" />
      <path d="M30.5 30.5 43 43" stroke="currentColor" strokeWidth="5" strokeLinecap="round" />
      <path d="M20 13v14M13 20h14" stroke="currentColor" strokeWidth="3.2" strokeLinecap="round" />
    </svg>
  ),
  check: (p: P) => (
    <svg {...S(p)}>
      <path d="m5 12.5 4.5 4.5L19 7.5" {...line} strokeWidth={2.4} />
    </svg>
  ),
  star: (p: P) => (
    <svg {...S(p)}>
      <path d="m12 3 2.7 5.6 6.1.8-4.5 4.2 1.1 6L12 16.7 6.6 19.6l1.1-6-4.5-4.2 6.1-.8z" fill="currentColor" />
    </svg>
  ),
  user: (p: P) => (
    <svg {...S(p)}>
      <circle cx="12" cy="8.5" r="3.8" {...line} strokeWidth={1.8} />
      <path d="M4.5 20a7.5 7.5 0 0 1 15 0" {...line} strokeWidth={1.8} />
    </svg>
  ),
  // ---- "We deliver" destinations (drawn on a 64px grid)
  home: (p: P) => (
    <svg {...S({ viewBox: "0 0 64 64", ...p })}>
      <g {...line} strokeWidth={2.2}>
        <path d="M6 30 32 9l26 21" />
        <path d="M12 26v28h40V26" />
        <path d="M26 54V40h12v14" />
        <rect x="16" y="32" width="8" height="8" />
        <rect x="40" y="32" width="8" height="8" />
        <path d="M44 15v-5h6v10" />
      </g>
    </svg>
  ),
  apartment: (p: P) => (
    <svg {...S({ viewBox: "0 0 64 64", ...p })}>
      <g {...line} strokeWidth={2.2}>
        <rect x="18" y="6" width="28" height="50" />
        <path d="M12 56h40" />
        {[13, 21, 29, 37].map((y) => (
          <g key={y}>
            <rect x="23" y={y} width="6" height="5" />
            <rect x="35" y={y} width="6" height="5" />
          </g>
        ))}
        <path d="M28 56v-9h8v9" />
      </g>
    </svg>
  ),
  office: (p: P) => (
    <svg {...S({ viewBox: "0 0 64 64", ...p })}>
      <g {...line} strokeWidth={2.2}>
        <path d="M6 56h52" />
        <rect x="10" y="20" width="22" height="36" />
        <rect x="32" y="10" width="22" height="46" />
        {[26, 34, 42].map((y) => (
          <g key={y}>
            <path d={`M15 ${y}h4M23 ${y}h4`} />
          </g>
        ))}
        {[17, 25, 33, 41].map((y) => (
          <path key={y} d={`M37 ${y}h4M45 ${y}h4`} />
        ))}
        <path d="M39 56v-7h8v7" />
      </g>
    </svg>
  ),
  hostel: (p: P) => (
    <svg {...S({ viewBox: "0 0 64 64", ...p })}>
      <g {...line} strokeWidth={2.2}>
        <path d="M8 56V22l24-14 24 14v34" />
        <path d="M4 56h56" />
        <path d="M16 46h32M16 46v-8h32v8M16 46v6M48 46v6" />
        <path d="M18 38v-4a3 3 0 0 1 3-3h6v7" />
        <circle cx="32" cy="22" r="4" />
      </g>
    </svg>
  ),
  school: (p: P) => (
    <svg {...S({ viewBox: "0 0 64 64", ...p })}>
      <g {...line} strokeWidth={2.2}>
        <path d="M4 56h56" />
        <path d="M10 56V30h44v26" />
        <path d="M6 30 32 16l26 14" />
        <circle cx="32" cy="30" r="5" />
        <path d="M32 27v3l2 1.5" />
        <path d="M32 16V6h8v4h-8" />
        <path d="M27 56V44h10v12" />
        <rect x="15" y="40" width="7" height="6" />
        <rect x="42" y="40" width="7" height="6" />
      </g>
    </svg>
  ),
  shop: (p: P) => (
    <svg {...S({ viewBox: "0 0 64 64", ...p })}>
      <g {...line} strokeWidth={2.2}>
        <path d="M4 56h56" />
        <path d="M10 30v26h44V30" />
        <path d="M8 18h48l4 10a6 6 0 0 1-12 0 6 6 0 0 1-12 0 6 6 0 0 1-12 0 6 6 0 0 1-12 0z" />
        <path d="M10 18 14 8h36l4 10" />
        <path d="M16 56V40h12v16" />
        <rect x="34" y="40" width="14" height="10" />
      </g>
    </svg>
  ),
};

export function Logo({ light = true }: { light?: boolean }) {
  return (
    <span className={"logo" + (light ? " logo--light" : "")}>
      <svg viewBox="0 0 40 40" width="38" height="38" aria-hidden="true">
        <defs>
          <linearGradient id="lg-drop" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#5aa8f0" />
            <stop offset="1" stopColor="#0b3f8c" />
          </linearGradient>
        </defs>
        <path d="M20 3S8 16.5 8 24.5a12 12 0 0 0 24 0C32 16.5 20 3 20 3Z" fill="url(#lg-drop)" />
        <path d="M11 27c4-4 7 4 11 0s7 3 7 3" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" />
        <path d="M14.5 21a6 6 0 0 1 4-6" fill="none" stroke="#fff" strokeWidth="2" strokeLinecap="round" opacity=".8" />
      </svg>
      <span className="logo-word">
        Jal<b>Setu</b>
      </span>
    </span>
  );
}
