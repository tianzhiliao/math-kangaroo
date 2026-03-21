"use client";

import { useQuery } from "@tanstack/react-query";
import type { Exam } from "@/lib/types";
import { ExamRun } from "./ExamRun";
import { PracticeRun } from "./PracticeRun";
import Link from "next/link";

function Loading() {
  return (
    <div className="flex min-h-[100dvh] flex-col items-center justify-center gap-3 text-slate-600">
      <span
        className="inline-block h-10 w-10 animate-spin rounded-full border-4 border-blue-500 border-t-transparent"
        aria-hidden
      />
      <span className="text-lg font-medium">Loading…</span>
    </div>
  );
}

function Fail() {
  return (
    <div className="flex min-h-[100dvh] flex-col items-center justify-center gap-4 p-6">
      <p className="text-lg text-slate-600">Could not load this exam.</p>
      <Link
        href="/"
        className="rounded-2xl bg-blue-500 px-6 py-3 font-bold text-white"
      >
        Back to Home
      </Link>
    </div>
  );
}

export function ExamSessionLoader({ examId }: { examId: string }) {
  const { data, isPending, error } = useQuery({
    queryKey: ["exam", examId],
    queryFn: async () => {
      const r = await fetch(`/api/exams/${encodeURIComponent(examId)}`);
      if (!r.ok) throw new Error("bad");
      return r.json() as Promise<Exam>;
    },
  });
  if (isPending) return <Loading />;
  if (error || !data) return <Fail />;
  return <ExamRun exam={data} />;
}

export function PracticeSessionLoader({ examId }: { examId: string }) {
  const { data, isPending, error } = useQuery({
    queryKey: ["exam", examId],
    queryFn: async () => {
      const r = await fetch(`/api/exams/${encodeURIComponent(examId)}`);
      if (!r.ok) throw new Error("bad");
      return r.json() as Promise<Exam>;
    },
  });
  if (isPending) return <Loading />;
  if (error || !data) return <Fail />;
  return <PracticeRun exam={data} />;
}
