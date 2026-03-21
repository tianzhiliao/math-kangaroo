import { HomeModeCard } from "@/components/home-mode-card";
import { getCatalog } from "@/lib/data";

export default async function HomePage() {
  const catalog = await getCatalog();

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-kicker">Math Kangaroo Prep</span>
          <h1 className="brand-title">Train one question at a time.</h1>
          <p className="brand-note">
            A focused prep studio built from {catalog.examCount} official papers and {catalog.questionCount} questions.
            Keep the rhythm calm, the screen minimal, and your attention on a single problem.
          </p>
        </div>
      </header>

      <section className="mode-grid">
        <HomeModeCard
          href="/exam"
          tone="exam"
          eyebrow="Full paper"
          title="Mock exam mode"
          description="Simulate the real paper with timing, scoring, jumping between questions, and a full results review once you submit."
          bullets={[
            "Choose any official paper and decide where to begin before the timer starts.",
            "Move freely across the paper, flag questions, and submit when you are ready.",
          ]}
          actionLabel="Open mock exams"
        />
        <HomeModeCard
          href="/practice"
          tone="practice"
          eyebrow="All questions"
          title="Practice mode"
          description="Work through the full question bank with immediate correctness feedback, random jumps, and local progress tracking."
          bullets={[
            "Filter by exam family, year, or paper, then start from any question.",
            "See the answer instantly after submitting and keep moving without breaking focus.",
          ]}
          actionLabel="Open practice"
        />
      </section>
    </main>
  );
}
