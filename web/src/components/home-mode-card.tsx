import Link from "next/link";

interface HomeModeCardProps {
  href: string;
  tone: "exam" | "practice";
  eyebrow: string;
  title: string;
  description: string;
  bullets: string[];
  actionLabel: string;
}

export function HomeModeCard({
  href,
  tone,
  eyebrow,
  title,
  description,
  bullets,
  actionLabel,
}: HomeModeCardProps) {
  return (
    <article className="panel mode-card animate-rise" data-tone={tone}>
      <div className="panel-inner" style={{ height: "100%", display: "grid", alignContent: "space-between" }}>
        <div>
          <div className="eyebrow">{eyebrow}</div>
          <h2 className="mode-title">{title}</h2>
          <p className="lede">{description}</p>
          <div className="divider" />
          <div className="field-stack">
            {bullets.map((bullet) => (
              <div className="status-banner" key={bullet}>
                <span className="mini-pill">{tone === "exam" ? "Timed" : "Instant"}</span>
                <p>{bullet}</p>
              </div>
            ))}
          </div>
        </div>
        <Link className="primary-button" href={href}>
          {actionLabel}
        </Link>
      </div>
    </article>
  );
}
