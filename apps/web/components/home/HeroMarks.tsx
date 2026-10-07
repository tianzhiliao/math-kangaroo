/**
 * Decorative sums scattered behind the home hero (plan-c.md §5.15).
 * Fixed positions (SSR-stable). Desktop marks sit outside the central 560px
 * text column and below the 72px nav.
 */
type Tone = "ink" | "blue" | "yellow" | "magenta";
type Mark = {
  text: string;
  side: "l" | "r";
  /** px from the edge of the 560px safe column (desktop) or % from the screen edge (phone). */
  x: number;
  y: number;
  size: 16 | 22 | 28;
  rotate: number;
  tone?: Tone;
};

const TONE: Record<Tone, string> = {
  ink: "text-mk-ink-12",
  blue: "text-mk-hue-blue opacity-[.85]",
  yellow: "text-mk-hue-yellow opacity-[.85]",
  magenta: "text-mk-hue-magenta opacity-[.85]",
};

const SIZE = {
  16: "text-[16px] leading-[20px]",
  22: "text-[22px] leading-[26px]",
  28: "text-[28px] leading-[32px]",
} as const;

const DESKTOP: Mark[] = [
  { text: "60 − 52 = 8", side: "l", x: 150, y: 108, size: 22, rotate: -2 },
  { text: "12", side: "l", x: 60, y: 84, size: 28, rotate: 3, tone: "blue" },
  { text: "45 min", side: "l", x: 220, y: 172, size: 28, rotate: 0 },
  { text: "8 kg", side: "l", x: 40, y: 206, size: 22, rotate: -3, tone: "blue" },
  { text: "△ □ ○", side: "l", x: 230, y: 266, size: 22, rotate: 0 },
  { text: "3 + 5", side: "l", x: 90, y: 340, size: 22, rotate: 4 },
  { text: "15", side: "l", x: 200, y: 444, size: 22, rotate: -2 },
  { text: "4 × 3", side: "l", x: 20, y: 470, size: 16, rotate: 2 },
  { text: "112", side: "l", x: 290, y: 400, size: 16, rotate: 0, tone: "magenta" },
  { text: "5 − 4 − 3 − 2 − 1", side: "r", x: 10, y: 92, size: 16, rotate: 2 },
  { text: "½", side: "r", x: 200, y: 112, size: 16, rotate: 0 },
  { text: "= ?", side: "r", x: 90, y: 176, size: 22, rotate: -3 },
  { text: "9 → 6", side: "r", x: 230, y: 244, size: 22, rotate: 2 },
  { text: "2 × 4", side: "r", x: 40, y: 374, size: 22, rotate: 0, tone: "yellow" },
  { text: "10", side: "r", x: 270, y: 396, size: 28, rotate: -4, tone: "magenta" },
  { text: "1 + 2 + 3", side: "r", x: 70, y: 476, size: 22, rotate: 3 },
  { text: "6 m", side: "r", x: 250, y: 498, size: 28, rotate: 0, tone: "yellow" },
  { text: "24", side: "r", x: 170, y: 300, size: 16, rotate: 2 },
  { text: "□□□", side: "r", x: 290, y: 168, size: 16, rotate: 0 },
  { text: "7", side: "l", x: 300, y: 236, size: 16, rotate: -4 },
];

/**
 * Phones: the text column is full-width, so marks only use the empty bands —
 * between the nav and the meta line (top) and under the buttons (bottom).
 */
const PHONE: (Omit<Mark, "y"> & { top?: number; bottom?: number })[] = [
  { text: "12", side: "l", x: 4, top: 70, size: 16, rotate: 3, tone: "blue" },
  { text: "△ □", side: "l", x: 28, top: 74, size: 16, rotate: 0 },
  { text: "= ?", side: "r", x: 30, top: 72, size: 16, rotate: -2 },
  { text: "8", side: "r", x: 6, top: 76, size: 16, rotate: -3 },
  { text: "3 + 5", side: "l", x: 6, bottom: 14, size: 16, rotate: -2 },
  { text: "10", side: "l", x: 38, bottom: 20, size: 16, rotate: 3, tone: "magenta" },
  { text: "2 × 4", side: "r", x: 30, bottom: 12, size: 16, rotate: 2 },
  { text: "6 m", side: "r", x: 5, bottom: 22, size: 16, rotate: 0, tone: "yellow" },
];

export function HeroMarks() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 select-none overflow-hidden font-mono"
    >
      <div className="absolute inset-0 hidden motion-safe:animate-[mk-drift_6s_linear_infinite] md:block">
        {DESKTOP.map((m) => (
          <span
            key={m.text}
            className={`absolute whitespace-nowrap ${SIZE[m.size]} ${TONE[m.tone ?? "ink"]}`}
            style={{
              top: m.y,
              transform: `rotate(${m.rotate}deg)`,
              ...(m.side === "l"
                ? { right: `calc(50% + 280px + ${m.x}px)` }
                : { left: `calc(50% + 280px + ${m.x}px)` }),
            }}
          >
            {m.text}
          </span>
        ))}
      </div>
      <div className="absolute inset-0 md:hidden">
        {PHONE.map((m) => (
          <span
            key={m.text}
            className={`absolute whitespace-nowrap ${SIZE[m.size]} ${TONE[m.tone ?? "ink"]}`}
            style={{
              top: m.top,
              bottom: m.bottom,
              transform: `rotate(${m.rotate}deg)`,
              [m.side === "l" ? "left" : "right"]: `${m.x}%`,
            }}
          >
            {m.text}
          </span>
        ))}
      </div>
    </div>
  );
}
