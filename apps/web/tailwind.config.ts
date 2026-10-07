import type { Config } from "tailwindcss";

type FontSizeValue = [
  string,
  { lineHeight: string; letterSpacing: string; fontWeight: string },
];

/** Plan C type scale: size / line-height / tracking / weight travel together. */
const type = (
  size: number,
  lineHeight: number,
  tracking: string,
  weight: 400 | 500 = 500,
): FontSizeValue => [
  `${size}px`,
  {
    lineHeight: `${lineHeight}px`,
    letterSpacing: tracking,
    fontWeight: String(weight),
  },
];

export default {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        mk: {
          bg: "var(--mk-bg)",
          ink: {
            100: "var(--mk-ink-100)",
            80: "var(--mk-ink-80)",
            60: "var(--mk-ink-60)",
            44: "var(--mk-ink-44)",
            12: "var(--mk-ink-12)",
            4: "var(--mk-ink-4)",
            2: "var(--mk-ink-2)",
          },
          raised: "var(--mk-raised)",
          "solid-12": "var(--mk-solid-12)",
          inverse: {
            DEFAULT: "var(--mk-inverse-fg)",
            60: "var(--mk-inverse-60)",
            20: "var(--mk-inverse-20)",
          },
          right: {
            strong: "var(--mk-right-strong)",
            surface: "var(--mk-right-surface)",
            soft: "var(--mk-right-soft)",
            fg: "var(--mk-right-fg)",
            dot: "var(--mk-right-dot)",
          },
          wrong: {
            strong: "var(--mk-wrong-strong)",
            surface: "var(--mk-wrong-surface)",
            soft: "var(--mk-wrong-soft)",
            subtle: "var(--mk-wrong-subtle)",
            fg: "var(--mk-wrong-fg)",
            dot: "var(--mk-wrong-dot)",
          },
          warn: {
            fg: "var(--mk-warn-fg)",
            bar: "var(--mk-warn-bar)",
          },
          hue: {
            blue: "var(--mk-hue-blue)",
            yellow: "var(--mk-hue-yellow)",
            magenta: "var(--mk-hue-magenta)",
          },
          series: {
            felix: "var(--mk-series-felix)",
            "level-p": "var(--mk-series-level-p)",
            "grade-1-2": "var(--mk-series-grade-1-2)",
          },
          scrim: "var(--mk-scrim)",
          focus: "var(--mk-focus)",
        },
      },
      fontFamily: {
        sans: ["var(--mk-font-sans)"],
        mono: ["var(--mk-font-mono)"],
      },
      // Desktop roles; `-m` variants are the < 768px values (plan-c.md §3.2).
      fontSize: {
        display: type(64, 64, "-0.03em"),
        "display-m": type(40, 44, "-0.03em"),
        score: type(48, 56, "-0.03em"),
        "score-m": type(40, 48, "-0.03em"),
        title: type(38, 44, "-0.02em"),
        "title-m": type(30, 36, "-0.02em"),
        stem: type(26, 34, "-0.01em"),
        "stem-m": type(21, 28, "-0.01em"),
        h4: type(22, 28, "-0.01em"),
        choice: type(22, 28, "-0.01em"),
        "choice-m": type(19, 26, "-0.01em"),
        h5: type(18, 24, "-0.01em"),
        p1: type(17, 28, "-0.01em", 400),
        explain: type(19, 30, "-0.01em", 400),
        "explain-m": type(17, 28, "-0.01em", 400),
        cta: type(15, 15, "0em"),
        meta: type(14, 20, "0em"),
        "meta-m": type(13, 18, "0em"),
        caption: type(13, 18, "0em"),
      },
      borderRadius: {
        md: "6px",
        card: "16px",
        panel: "24px",
        button: "2.5rem",
      },
      boxShadow: {
        popover: "var(--mk-shadow-popover)",
      },
    },
  },
  plugins: [],
} satisfies Config;
