"use client";

import { useQuery } from "@tanstack/react-query";
import type { Manifest } from "@/lib/types";
import Link from "next/link";
import { useMemo } from "react";

export default function ExamPickerPage() {
  const { data, isPending } = useQuery({
    queryKey: ["manifest"],
    queryFn: async () => {
      const r = await fetch("/api/exams");
      if (!r.ok) throw new Error("bad");
      return r.json() as Promise<Manifest>;
    },
  });

  const sortedExams = useMemo(() => {
    if (!data?.exams?.length) return [];
    return [...data.exams].sort((a, b) => {
      if (b.year !== a.year) return b.year - a.year;
      return a.exam_id.localeCompare(b.exam_id);
    });
  }, [data?.exams]);

  /** Same calendar year → "2023-1", "2023-2"; single exam for that year → "2023". */
  const yearLabelByExamId = useMemo(() => {
    const countByYear = new Map<number, number>();
    for (const e of sortedExams) {
      countByYear.set(e.year, (countByYear.get(e.year) ?? 0) + 1);
    }
    const indexInYear = new Map<number, number>();
    const map = new Map<string, string>();
    for (const e of sortedExams) {
      const n = countByYear.get(e.year) ?? 1;
      if (n > 1) {
        const next = (indexInYear.get(e.year) ?? 0) + 1;
        indexInYear.set(e.year, next);
        map.set(e.exam_id, `${e.year}-${next}`);
      } else {
        map.set(e.exam_id, String(e.year));
      }
    }
    return map;
  }, [sortedExams]);

  if (isPending) {
    return (
      <div className="flex min-h-[100dvh] flex-col items-center justify-center gap-3 text-slate-600">
        <span
          className="inline-block h-10 w-10 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"
          aria-hidden
        />
        <span className="text-lg font-medium">Loading exams…</span>
      </div>
    );
  }

  if (!sortedExams.length) {
    return (
      <div className="p-8 text-center">
        <p className="text-slate-600">No exams available yet.</p>
        <Link href="/" className="mt-4 inline-block font-bold text-blue-600">
          Back to Home
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto flex min-h-[100dvh] w-full max-w-6xl flex-col gap-6 p-4 sm:p-6">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          href="/"
          className="tap-target rounded-xl bg-slate-200 px-4 text-sm font-bold text-slate-800"
        >
          Back to Home
        </Link>
      </div>
      <h1 className="text-2xl font-black text-slate-900">Choose a year</h1>
      <p className="-mt-2 text-slate-600">
        Tap a year to start a timed exam for that paper.
      </p>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(13rem,1fr))] gap-4 sm:gap-5">
        {sortedExams.map((e) => (
          <Link
            key={e.exam_id}
            href={`/exam/${encodeURIComponent(e.exam_id)}`}
            className="tap-target flex min-h-[5.5rem] flex-col items-center justify-center rounded-2xl border-2 border-slate-200 bg-white px-4 py-6 text-center shadow-sm transition hover:border-blue-400 hover:shadow-md sm:min-h-[6rem]"
          >
            <span className="text-3xl font-black tabular-nums text-slate-900">
              {yearLabelByExamId.get(e.exam_id) ?? String(e.year)}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
