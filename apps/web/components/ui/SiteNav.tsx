import Link from "next/link";

/** Transparent top navigation for the home and paper-picker pages. */
export function SiteNav({ current }: { current?: "exam" | "practice" }) {
  const item = (key: "exam" | "practice", href: string, label: string) => (
    <Link
      href={href}
      aria-current={current === key ? "page" : undefined}
      className={`mk-transition-fast tap-target px-2 text-meta underline-offset-4 hover:text-mk-ink-100 hover:underline focus-visible:underline ${
        current && current !== key ? "text-mk-ink-60" : "text-mk-ink-100"
      }`}
    >
      {label}
    </Link>
  );
  return (
    <nav
      aria-label="Main"
      className="relative z-10 flex h-[64px] items-center justify-between px-4 md:px-8"
    >
      <Link
        href="/"
        className="mk-transition-fast tap-target -ml-1 px-1 text-h5 underline-offset-4 hover:underline focus-visible:underline"
      >
        Math Kangaroo
      </Link>
      <div className="flex items-center gap-2 md:gap-4">
        {item("exam", "/exam", "Exam")}
        {item("practice", "/practice", "Practice")}
      </div>
    </nav>
  );
}
