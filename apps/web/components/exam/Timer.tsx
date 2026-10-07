const LOW_TIME_SEC = 5 * 60;

export function formatTime(totalSeconds: number): string {
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/** Screen-reader text: changes once a minute, then once for the last minute. */
function spokenTime(secondsLeft: number): string {
  if (secondsLeft <= 0) return "Time is up";
  if (secondsLeft <= 60) return "Less than 1 minute left";
  const minutes = Math.ceil(secondsLeft / 60);
  return `${minutes} minutes left`;
}

/** Remaining time, always visible, amber under 5 minutes (plan-c.md §5.4). */
export function Timer({
  secondsLeft,
  durationSec,
}: {
  secondsLeft: number;
  durationSec: number;
}) {
  const low = secondsLeft < LOW_TIME_SEC;
  const remainingPercent = Math.round((secondsLeft / durationSec) * 100);
  return (
    <div className="flex w-[140px] flex-col items-end gap-1.5">
      <p
        className={`mk-transition text-meta tabular-nums ${low ? "text-mk-warn-fg" : "text-mk-ink-100"}`}
        aria-hidden
      >
        {formatTime(secondsLeft)} left
      </p>
      <span className="sr-only" aria-live="polite">
        {spokenTime(secondsLeft)}
      </span>
      <div
        className="h-1 w-full overflow-hidden rounded-full bg-mk-ink-4"
        role="progressbar"
        aria-label="Exam time remaining"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={remainingPercent}
        aria-valuetext={`${formatTime(secondsLeft)} left`}
      >
        <div
          className={`h-full rounded-full transition-[width,background-color] duration-1000 ease-linear ${low ? "bg-mk-warn-bar" : "bg-mk-ink-100"}`}
          style={{ width: `${remainingPercent}%` }}
        />
      </div>
    </div>
  );
}
