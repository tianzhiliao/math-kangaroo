/** 20px line icons, 1.6px stroke, currentColor (plan-c.md §5.2). */
type IconProps = { className?: string };

function Svg({
  className = "h-5 w-5",
  children,
}: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

export function ChevronLeftIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m14.5 6-6 6 6 6" />
    </Svg>
  );
}

export function SpeakerIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M11 5 6 9H3v6h3l5 4V5Z" />
      <path d="M15.5 8.5a5 5 0 0 1 0 7" />
      <path d="M18 6a8 8 0 0 1 0 12" />
    </Svg>
  );
}

export function RefreshIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3" />
      <path d="M19.5 4.5v4h-4" />
    </Svg>
  );
}

export function CheckIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m5 12.5 4.5 4.5L19 7.5" />
    </Svg>
  );
}

export function CrossIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="m6.5 6.5 11 11M17.5 6.5l-11 11" />
    </Svg>
  );
}

/** Loading ring; spins unless reduced motion (globals.css zeroes animations). */
export function Spinner({ className = "h-4 w-4" }: IconProps) {
  return (
    <span
      aria-hidden
      className={`inline-block animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
    />
  );
}
