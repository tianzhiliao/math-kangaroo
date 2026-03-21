import Link from "next/link";

interface PageChromeProps {
  kicker: string;
  title: string;
  note: string;
  active: "home" | "exam" | "practice";
  children: React.ReactNode;
}

export function PageChrome({ kicker, title, note, active, children }: PageChromeProps) {
  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-kicker">{kicker}</span>
          <h1 className="brand-title">{title}</h1>
          <p className="brand-note">{note}</p>
        </div>
        <nav className="nav-row" aria-label="Primary">
          <Link className="nav-link" href="/" data-active={active === "home"}>
            Home
          </Link>
          <Link className="nav-link" href="/exam" data-active={active === "exam"}>
            Mock exams
          </Link>
          <Link className="nav-link" href="/practice" data-active={active === "practice"}>
            Practice
          </Link>
        </nav>
      </header>
      {children}
    </main>
  );
}
