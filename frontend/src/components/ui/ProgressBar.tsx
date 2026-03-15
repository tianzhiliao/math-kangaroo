import { cn } from "../../lib/utils"

interface ProgressBarProps {
  current: number
  total: number
  className?: string
}

export function ProgressBar({ current, total, className }: ProgressBarProps) {
  const percentage = total > 0 ? Math.min(100, Math.max(0, (current / total) * 100)) : 0

  return (
    <div
      className={cn(
        "h-4 w-full overflow-hidden rounded-full bg-slate-100 shadow-inner",
        className,
      )}
    >
      <div
        className="h-full rounded-full bg-[linear-gradient(90deg,#58CC02_0%,#8BE23A_100%)] transition-all duration-500 ease-out"
        style={{ width: `${percentage}%` }}
      />
    </div>
  )
}
