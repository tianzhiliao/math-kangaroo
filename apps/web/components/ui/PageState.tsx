import { Spinner } from "./icons";

/**
 * Full-page loading / empty / error state (plan-c.md §5.14).
 * With no title it renders as a loading state.
 */
export function PageState({
  title,
  message,
  actions,
}: {
  title?: string;
  message: string;
  actions?: React.ReactNode;
}) {
  const loading = !title;
  return (
    <div
      className="flex min-h-[100dvh] flex-col items-center justify-center gap-4 px-4 text-center"
      role={loading ? "status" : undefined}
    >
      {loading ? (
        <>
          <Spinner className="h-7 w-7 text-mk-ink-100" />
          <p className="text-[15px] font-medium leading-5 text-mk-ink-60">
            {message}
          </p>
        </>
      ) : (
        <>
          <div className="max-w-md">
            <h1 className="text-h4">{title}</h1>
            <p className="mt-2 text-p1 text-mk-ink-60">{message}</p>
          </div>
          {actions ? (
            <div className="flex flex-wrap items-center justify-center gap-3">
              {actions}
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
