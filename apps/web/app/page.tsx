"use client";

import Link from "next/link";
import { useMemo } from "react";
import { HeroMarks } from "@/components/home/HeroMarks";
import { ButtonLink } from "@/components/ui/Button";
import { SiteNav } from "@/components/ui/SiteNav";
import { usePracticeAnswersStore } from "@/lib/practice-answers-store";
import { useManifest, usePracticeBank } from "@/lib/queries";
import { SERIES } from "@/lib/series";
import { useHydrated } from "@/lib/use-hydrated";

const SHORT_SERIES_NAME: Record<string, string> = {
  felix: "Felix",
  "level-p": "Level P",
  "grade-1-2": "Grade 1–2",
};

function HomeCard({
  href,
  meta,
  title,
  children,
}: {
  href: string;
  meta: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="mk-transition flex flex-col gap-2 rounded-card border border-mk-ink-12 bg-mk-bg p-7 hover:border-mk-ink-44"
    >
      <p className="text-meta text-mk-ink-60">{meta}</p>
      <h2 className="text-h4">{title}</h2>
      {children}
    </Link>
  );
}

export default function Home() {
  const hydrated = useHydrated();
  const answers = usePracticeAnswersStore((s) => s.answers);
  const lastVisitedQuestion = usePracticeAnswersStore(
    (s) => s.lastVisitedQuestion,
  );
  const { data: bank } = usePracticeBank();
  const { data: manifest } = useManifest();

  const total = bank?.total ?? 0;
  const done = hydrated
    ? Object.keys(answers).filter((k) => {
        const n = Number(k);
        return n >= 1 && (!total || n <= total);
      }).length
    : 0;
  const resumeAt =
    hydrated &&
    typeof lastVisitedQuestion === "number" &&
    lastVisitedQuestion >= 1 &&
    (!total || lastVisitedQuestion <= total)
      ? lastVisitedQuestion
      : null;

  const heroMeta = useMemo(() => {
    const exams = manifest?.exams ?? [];
    if (!exams.length) return null;
    const levels = new Set(exams.map((e) => e.level));
    const names = SERIES.filter((s) => levels.has(s.key)).map(
      (s) => SHORT_SERIES_NAME[s.key] ?? s.name,
    );
    const years = exams.map((e) => e.year);
    const from = Math.min(...years);
    const to = Math.max(...years);
    return [...names, from === to ? `${from}` : `${from}–${to}`].join(" · ");
  }, [manifest]);

  const paperCount = manifest?.exams.length ?? 0;

  return (
    <main className="min-h-[100dvh] bg-mk-bg pb-16">
      <div className="relative">
        <HeroMarks />
        <SiteNav />
        <section className="relative mx-auto flex max-w-[560px] flex-col items-center px-4 pb-14 pt-12 text-center md:pb-[72px] md:pt-[72px]">
          <p className="min-h-[20px] text-meta text-mk-ink-60">{heroMeta}</p>
          <h1 className="mt-4 text-balance text-display-m md:text-display">
            Get ready for Math Kangaroo
          </h1>
          <p className="mt-6 text-pretty text-p1 text-mk-ink-80">
            {total ? `${total} real contest questions. ` : "Real contest questions. "}
            Sit a timed past paper, or practise one question at a time—with the
            right answer and a short explanation after every try.
          </p>
          <div className="mt-8 flex w-full flex-col items-stretch justify-center gap-3 sm:w-auto sm:flex-row sm:items-center">
            {resumeAt ? (
              <ButtonLink href={`/practice/q/${resumeAt}`}>
                Continue practice at question {resumeAt}
              </ButtonLink>
            ) : (
              <ButtonLink href="/practice">Start practice</ButtonLink>
            )}
            <ButtonLink href="/exam" variant="secondary">
              Choose an exam paper
            </ButtonLink>
          </div>
        </section>
      </div>

      <div className="mx-auto grid max-w-[1120px] grid-cols-[repeat(auto-fit,minmax(min(100%,320px),1fr))] gap-6 px-4 md:px-8">
        <HomeCard
          href="/exam"
          meta={paperCount ? `Exam · ${paperCount} papers` : "Exam"}
          title="Sit a timed past paper"
        >
          <p className="text-p1 text-mk-ink-80">
            Scored like the contest: right answers earn 3, 4 or 5 points, wrong
            ones cost 1.
          </p>
        </HomeCard>
        <HomeCard
          href="/practice"
          meta={
            total ? (
              <span className="tabular-nums">
                Practice · {done} of {total} done
              </span>
            ) : (
              "Practice"
            )
          }
          title="Learn one question at a time"
        >
          {total ? (
            <div
              className="my-2 h-1 overflow-hidden rounded-full bg-mk-ink-4"
              role="progressbar"
              aria-label="Practice progress"
              aria-valuemin={0}
              aria-valuemax={total}
              aria-valuenow={done}
            >
              <div
                className="h-full rounded-full bg-mk-ink-100"
                style={{ width: `${(done / total) * 100}%` }}
              />
            </div>
          ) : null}
          <p className="text-p1 text-mk-ink-80">
            Listen to each question, see the answer straight away, then try a
            similar one.
          </p>
        </HomeCard>
      </div>
    </main>
  );
}
