import Link from "next/link";
import type { ManifestExamEntry } from "@/lib/types";
import { seriesFor } from "@/lib/series";

/** One past paper in the picker grid (plan-c.md §5.13). */
export function PaperCard({ exam }: { exam: ManifestExamEntry }) {
  const series = seriesFor(exam.level, exam.family);
  return (
    <Link
      href={`/exam/${encodeURIComponent(exam.exam_id)}`}
      aria-label={`${series.name} ${exam.year}, ${exam.question_count} questions`}
      className="group flex flex-col gap-1 rounded-card"
    >
      <div
        className={`mk-transition flex h-[104px] items-end rounded-card px-5 pb-3 outline outline-1 outline-offset-0 outline-transparent group-hover:outline-mk-ink-12 ${series.coverClassName}`}
      >
        <span className="text-[30px] font-medium leading-9 tracking-[-0.02em] tabular-nums">
          {exam.year}
        </span>
      </div>
      <p className="mt-3 text-meta text-mk-ink-60 tabular-nums">
        {exam.question_count} questions
      </p>
      <p className="text-h5">{series.name}</p>
    </Link>
  );
}
