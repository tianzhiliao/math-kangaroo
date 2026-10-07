import { CheckIcon, CrossIcon } from "@/components/ui/icons";

export type PillTone = "right" | "wrong" | "neutral";

const TONE: Record<PillTone, string> = {
  right: "bg-mk-right-soft text-mk-right-fg",
  wrong: "bg-mk-wrong-soft text-mk-wrong-fg",
  neutral: "bg-mk-raised text-mk-ink-100",
};

/** Rounded outcome pill with an icon — colour never carries the meaning alone. */
export function OutcomePill({
  tone,
  children,
  size = "lg",
  live = false,
}: {
  tone: PillTone;
  children: React.ReactNode;
  size?: "lg" | "sm";
  live?: boolean;
}) {
  const Icon = tone === "right" ? CheckIcon : CrossIcon;
  return (
    <p
      aria-live={live ? "polite" : undefined}
      className={`inline-flex max-w-full items-center rounded-full ${TONE[tone]} ${
        size === "lg"
          ? "gap-2 px-4 py-2 text-[15px] font-medium leading-5 md:px-5 md:py-3 md:text-[18px] md:leading-6"
          : "gap-1.5 px-4 py-1.5 text-meta"
      }`}
    >
      <Icon className={`shrink-0 ${size === "lg" ? "h-[18px] w-[18px]" : "h-4 w-4"}`} />
      <span className="min-w-0">{children}</span>
    </p>
  );
}

/** Practice feedback after answering (plan-c.md §5.8). */
export function FeedbackPill({
  isCorrect,
  correctLabel,
  correctText,
}: {
  isCorrect: boolean;
  correctLabel: string;
  correctText?: string;
}) {
  const answer = correctText?.trim()
    ? `${correctLabel}, ${correctText.trim()}`
    : correctLabel;
  return (
    <OutcomePill tone={isCorrect ? "right" : "wrong"} live>
      {isCorrect
        ? `Right—the answer is ${answer}`
        : `Not quite—the right answer is ${answer}`}
    </OutcomePill>
  );
}
