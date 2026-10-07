export type LegendDot =
  | "now"
  | "answered"
  | "empty"
  | "right"
  | "wrong"
  | "skipped";

const DOT: Record<LegendDot, string> = {
  now: "bg-mk-ink-100",
  answered: "bg-mk-solid-12",
  empty: "border border-mk-ink-60 bg-mk-bg",
  right: "bg-mk-right-dot",
  wrong: "bg-mk-wrong-dot",
  skipped: "border border-dashed border-mk-ink-60 bg-mk-bg",
};

export type LegendItem = { dot: LegendDot; label: string };

export const EXAM_LEGEND: LegendItem[] = [
  { dot: "now", label: "Now" },
  { dot: "answered", label: "Answered" },
  { dot: "empty", label: "Not yet" },
];

export const RESULT_LEGEND: LegendItem[] = [
  { dot: "right", label: "Right" },
  { dot: "wrong", label: "Wrong" },
  { dot: "skipped", label: "Skipped" },
];

export const PRACTICE_LEGEND: LegendItem[] = [
  { dot: "right", label: "Right" },
  { dot: "wrong", label: "Wrong" },
  { dot: "empty", label: "Not tried" },
];

export function StatusLegend({ items }: { items: LegendItem[] }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-2" aria-label="Legend">
      {items.map((item) => (
        <li
          key={item.label}
          className="flex items-center gap-1.5 text-caption text-mk-ink-60"
        >
          <span
            aria-hidden
            className={`h-2.5 w-2.5 shrink-0 rounded-full ${DOT[item.dot]}`}
          />
          {item.label}
        </li>
      ))}
    </ul>
  );
}
