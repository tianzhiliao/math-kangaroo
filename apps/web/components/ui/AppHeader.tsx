import { ChevronLeftIcon } from "./icons";
import { IconButton, IconLink } from "./IconButton";

type Back =
  | { href: string; onClick?: never; label: string }
  | { onClick: () => void; href?: never; label: string };

/**
 * 64px (54px on phones) page header for exam, result and practice screens:
 * back button · meta + title · right-hand slot (plan-c.md §5.3).
 */
export function AppHeader({
  back,
  meta,
  title,
  right,
  /** Put the right slot on its own full-width row below 768px (exam timer + submit). */
  rightBelowOnMobile = false,
}: {
  back: Back;
  meta?: React.ReactNode;
  title: React.ReactNode;
  right?: React.ReactNode;
  rightBelowOnMobile?: boolean;
}) {
  const backIcon = <ChevronLeftIcon />;
  return (
    <header className="flex shrink-0 flex-wrap items-center gap-x-3 gap-y-2 border-b border-mk-ink-12 bg-mk-bg px-2 py-[5px] md:min-h-[64px] md:px-6 md:py-2">
      <div className="flex min-h-[44px] min-w-0 flex-1 items-center gap-1 md:gap-2">
        {back.href !== undefined ? (
          <IconLink href={back.href} tone="plain" aria-label={back.label}>
            {backIcon}
          </IconLink>
        ) : (
          <IconButton tone="plain" aria-label={back.label} onClick={back.onClick}>
            {backIcon}
          </IconButton>
        )}
        <div className="min-w-0 flex-1 text-center md:text-left">
          {meta ? (
            <p className="hidden truncate text-meta text-mk-ink-60 md:block">
              {meta}
            </p>
          ) : null}
          <h1 className="truncate text-[16px] font-medium leading-[22px] tracking-[-0.01em] tabular-nums md:text-h5">
            {title}
          </h1>
        </div>
      </div>
      {right ? (
        <div
          className={`flex items-center gap-2 md:gap-3 ${
            rightBelowOnMobile
              ? "w-full justify-between px-2 pb-1 md:w-auto md:justify-end md:p-0"
              : ""
          }`}
        >
          {right}
        </div>
      ) : null}
    </header>
  );
}
