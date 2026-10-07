import type { TierBreakdown } from "@/lib/scoring";

const TIER_FILL = ["bg-mk-hue-blue", "bg-mk-hue-yellow", "bg-mk-hue-magenta"];

/** Result score, per-tier bars and right / wrong / skipped tiles (plan-c.md §5.12). */
export function ScoreCard({
  score,
  maxScore,
  tiers,
  right,
  wrong,
  skipped,
}: {
  score: number;
  maxScore: number;
  tiers: TierBreakdown[];
  right: number;
  wrong: number;
  skipped: number;
}) {
  const tile = (n: number, label: string, cls: string) => (
    <div className={`flex flex-col items-center rounded-md px-2 py-2.5 ${cls}`}>
      <span className="text-h4 tabular-nums">{n}</span>
      <span className="text-caption">{label}</span>
    </div>
  );
  return (
    <div className="flex flex-col gap-3">
      <section
        aria-label="Score"
        className="rounded-panel bg-mk-ink-100 p-[22px] text-mk-inverse"
      >
        <p className="text-meta text-mk-inverse-60">Score</p>
        <p className="mt-1 flex items-baseline gap-2">
          <span className="text-score-m tabular-nums md:text-score">{score}</span>
          <span className="text-p1 text-mk-inverse-60 tabular-nums">
            of {maxScore}
          </span>
        </p>
        <ul className="mt-4 flex flex-col gap-3">
          {tiers.map((t, i) => (
            <li key={`${t.from}-${t.to}`}>
              <div className="flex items-start justify-between gap-3 text-caption">
                <span>
                  Questions {t.from}–{t.to} · {t.points} points each
                </span>
                <span className="shrink-0 tabular-nums">
                  {t.earned} / {t.max}
                </span>
              </div>
              <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-mk-inverse-20">
                <div
                  className={`h-full rounded-full ${TIER_FILL[i % TIER_FILL.length]}`}
                  style={{ width: t.max ? `${(t.earned / t.max) * 100}%` : 0 }}
                />
              </div>
            </li>
          ))}
        </ul>
      </section>
      <div className="grid grid-cols-3 gap-2">
        {tile(right, "right", "bg-mk-right-soft text-mk-right-fg")}
        {tile(wrong, "wrong", "bg-mk-wrong-soft text-mk-wrong-fg")}
        {tile(skipped, "skipped", "bg-mk-raised text-mk-ink-100")}
      </div>
    </div>
  );
}
