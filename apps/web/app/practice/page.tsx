"use client";

import { useQuery } from "@tanstack/react-query";
import type { PracticeBankResponse } from "@/lib/types";
import Link from "next/link";

export default function PracticeIndexPage() {
  const { data: bank, isPending } = useQuery({
    queryKey: ["practice-bank"],
    queryFn: async () => {
      const r = await fetch("/api/practice-bank");
      if (!r.ok) throw new Error("bad");
      return r.json() as Promise<PracticeBankResponse>;
    },
  });

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
    <div className="mx-auto flex min-h-[100dvh] max-w-5xl flex-col gap-6 p-4 sm:p-6">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          href="/"
          className="tap-target rounded-xl bg-slate-200 px-4 text-sm font-bold text-slate-800"
        >
          Back to Home
        </Link>
      </div>
      <header>
        <h1 className="text-2xl font-black text-slate-900 sm:text-3xl">
          Practice · Math Kangaroo
        </h1>
      </header>

      <div
        className="grid grid-cols-[repeat(auto-fill,minmax(3rem,1fr))] gap-3 overflow-y-auto rounded-3xl border border-slate-200/80 bg-gradient-to-b from-white to-slate-50/80 p-4 shadow-inner sm:grid-cols-[repeat(auto-fill,minmax(3.25rem,1fr))] sm:gap-4 sm:p-5"
        role="list"
        aria-label="All practice questions"
      >
        {Array.from({ length: bank.total }, (_, i) => {
          const n = i + 1;
          return (
            <Link
              key={n}
              href={`/practice/q/${n}`}
              className="flex h-12 w-full min-w-0 items-center justify-center rounded-2xl border border-slate-200/90 bg-white px-2 text-sm font-bold text-slate-800 shadow-sm ring-1 ring-slate-100 transition hover:border-emerald-300 hover:bg-emerald-50/80 hover:shadow-md hover:ring-emerald-200/60 active:scale-[0.98] sm:h-[3.25rem] sm:text-base"
            >
              {n}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
