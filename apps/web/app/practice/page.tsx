"use client";

import { useQuery } from "@tanstack/react-query";
import type { PracticeBankResponse } from "@/lib/types";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { usePracticeAnswersStore } from "@/lib/practice-answers-store";

export default function PracticeIndexPage() {
  const router = useRouter();
  const lastVisitedQuestion = usePracticeAnswersStore(
    (s) => s.lastVisitedQuestion,
  );
  const { data: bank, isPending } = useQuery({
    queryKey: ["practice-bank"],
    queryFn: async () => {
      const r = await fetch("/api/practice-bank");
      if (!r.ok) throw new Error("bad");
      return r.json() as Promise<PracticeBankResponse>;
    },
  });
  const total = bank?.total ?? 0;
  const targetQuestion =
    typeof lastVisitedQuestion === "number" &&
    lastVisitedQuestion >= 1 &&
    lastVisitedQuestion <= total
      ? lastVisitedQuestion
      : 1;

  useEffect(() => {
    if (isPending || total < 1) return;
    router.replace(`/practice/q/${targetQuestion}`);
  }, [isPending, router, targetQuestion, total]);

  if (isPending) {
    return (
      <div className="flex min-h-[100dvh] flex-col items-center justify-center gap-3 text-slate-600">
        <span
          className="inline-block h-10 w-10 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent"
          aria-hidden
        />
        <span className="text-lg font-medium">Loading question bank…</span>
      </div>
    );
  }

  if (!bank?.total) {
    return (
      <div className="p-8 text-center">
        <p className="text-slate-600">No questions available yet.</p>
        <Link href="/" className="mt-4 inline-block font-bold text-emerald-600">
          Back to Home
        </Link>
      </div>
    );
  }

  return (
    <div className="flex min-h-[100dvh] flex-col items-center justify-center gap-3 text-slate-600">
      <span
        className="inline-block h-10 w-10 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent"
        aria-hidden
      />
      <span className="text-lg font-medium">Opening practice…</span>
    </div>
  );
}
