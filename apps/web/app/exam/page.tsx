"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useMemo } from "react";
import { PaperCard } from "@/components/exam/PaperCard";
import { Button, ButtonLink } from "@/components/ui/Button";
import { PageState } from "@/components/ui/PageState";
import { SiteNav } from "@/components/ui/SiteNav";
import { useManifest } from "@/lib/queries";
import { SERIES } from "@/lib/series";

const SERIES_ORDER = new Map(SERIES.map((s, i) => [s.key, i]));

function ExamPicker() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { data, isPending, isError, refetch } = useManifest();

  const sortedExams = useMemo(() => {
    if (!data?.exams?.length) return [];
    return [...data.exams].sort((a, b) => {
      if (b.year !== a.year) return b.year - a.year;
      const sa = SERIES_ORDER.get(a.level) ?? SERIES.length;
      const sb = SERIES_ORDER.get(b.level) ?? SERIES.length;
      if (sa !== sb) return sa - sb;
      return a.exam_id.localeCompare(b.exam_id);
    });
  }, [data?.exams]);

  const filters = useMemo(() => {
    const levels = new Set(sortedExams.map((e) => e.level));
    return SERIES.filter((s) => levels.has(s.key));
  }, [sortedExams]);

  const requested = searchParams.get("series");
  const active = filters.some((f) => f.key === requested) ? requested : null;
  const visible = active
    ? sortedExams.filter((e) => e.level === active)
    : sortedExams;

  const setFilter = (key: string | null) => {
    const params = new URLSearchParams(searchParams.toString());
    if (key) params.set("series", key);
    else params.delete("series");
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };

  if (isPending) return <PageState message="Loading papers…" />;

  if (isError) {
    return (
      <PageState
        title="Could not load the papers"
        message="Check the connection and try again."
        actions={
          <>
            <Button onClick={() => void refetch()}>Try again</Button>
            <ButtonLink href="/" variant="secondary">
              Back to home
            </ButtonLink>
          </>
        }
      />
    );
  }

  if (!sortedExams.length) {
    return (
      <PageState
        title="No papers yet"
        message="They appear here once added."
        actions={
          <ButtonLink href="/" variant="secondary">
            Back to home
          </ButtonLink>
        }
      />
    );
  }

  const pill = (key: string | null, label: string) => {
    const selected = active === key;
    return (
      <button
        key={key ?? "all"}
        type="button"
        aria-pressed={selected}
        onClick={() => setFilter(key)}
        className={`mk-transition min-h-[44px] whitespace-nowrap rounded-full px-[18px] text-[14px] font-medium leading-5 ${
          selected
            ? "bg-mk-ink-100 text-mk-inverse"
            : "bg-mk-raised text-mk-ink-100 hover:bg-mk-solid-12"
        }`}
      >
        {label}
      </button>
    );
  };

  return (
    <div className="mx-auto w-full max-w-[1216px] px-4 pb-16 pt-6 md:px-8 md:pt-10">
      <h1 className="text-title-m md:text-title">Choose a paper</h1>
      <p className="mt-3 max-w-[600px] text-p1 text-mk-ink-80">
        The timer starts when the paper opens. Move between questions freely
        and change answers until you submit.
      </p>
      <div
        className="-mx-4 mt-8 flex gap-2 overflow-x-auto px-4 pb-1 md:mx-0 md:flex-wrap md:px-0"
        role="group"
        aria-label="Filter by series"
      >
        {pill(null, "All")}
        {filters.map((f) => pill(f.key, f.name))}
      </div>
      <div className="mt-8 grid grid-cols-[repeat(auto-fill,minmax(min(100%,260px),1fr))] gap-x-4 gap-y-6">
        {visible.map((e) => (
          <PaperCard key={e.exam_id} exam={e} />
        ))}
      </div>
    </div>
  );
}

export default function ExamPickerPage() {
  return (
    <main className="min-h-[100dvh] bg-mk-bg">
      <SiteNav current="exam" />
      <Suspense fallback={<PageState message="Loading papers…" />}>
        <ExamPicker />
      </Suspense>
    </main>
  );
}
