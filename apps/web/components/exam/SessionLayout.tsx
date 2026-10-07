/**
 * Shared frame for exam, result and practice screens: header, left sidebar
 * (a horizontal strip below 768px), a scrolling 860px content column and a
 * footer pinned to the bottom of the viewport.
 */
export function SessionLayout({
  header,
  sidebar,
  sidebarClassName = "md:w-[250px]",
  footer,
  children,
}: {
  header: React.ReactNode;
  sidebar: React.ReactNode;
  sidebarClassName?: string;
  footer?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-[100dvh] flex-col bg-mk-bg">
      {header}
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        <aside
          className={`flex shrink-0 flex-col border-b border-mk-ink-12 md:gap-5 md:overflow-y-auto md:border-b-0 md:border-r md:p-6 ${sidebarClassName}`}
        >
          {sidebar}
        </aside>
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <main className="min-h-0 flex-1 overflow-y-auto">
            <div className="mx-auto flex w-full max-w-[860px] flex-col gap-6 px-4 py-5 md:px-12 md:py-10">
              {children}
            </div>
          </main>
          {footer ? (
            <footer className="shrink-0 border-t border-mk-ink-12 bg-mk-bg px-4 pb-[max(20px,env(safe-area-inset-bottom))] pt-3 md:px-12 md:py-4">
              <div className="mx-auto w-full max-w-[860px]">{footer}</div>
            </footer>
          ) : null}
        </div>
      </div>
    </div>
  );
}

/** Previous · centre label · Next. The centre label hides on phones. */
export function SessionFooterNav({
  top,
  previous,
  center,
  next,
}: {
  /** Shown above the buttons on phones only (practice feedback pill). */
  top?: React.ReactNode;
  previous: React.ReactNode;
  center?: React.ReactNode;
  next: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3">
      {top ? <div className="md:hidden">{top}</div> : null}
      <div className="grid grid-cols-[1fr_2fr] items-center gap-3 md:flex md:justify-between">
        <div className="[&>*]:w-full md:[&>*]:w-auto">{previous}</div>
        {center ? (
          <div className="hidden text-center text-meta text-mk-ink-60 tabular-nums md:block">
            {center}
          </div>
        ) : null}
        <div className="[&>*]:w-full md:[&>*]:w-auto">{next}</div>
      </div>
    </div>
  );
}
