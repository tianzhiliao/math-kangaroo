import Link from "next/link";
import { forwardRef } from "react";

type Tone = "raised" | "plain";

const TONE: Record<Tone, string> = {
  raised: "bg-mk-raised text-mk-ink-100 hover:bg-mk-solid-12",
  plain: "bg-transparent text-mk-ink-60 hover:bg-mk-ink-4 hover:text-mk-ink-100",
};

export function iconButtonClassName(tone: Tone = "raised", className = "") {
  return `mk-transition inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full ${TONE[tone]} ${className}`;
}

type IconButtonProps = Omit<
  React.ButtonHTMLAttributes<HTMLButtonElement>,
  "aria-label"
> & {
  "aria-label": string;
  tone?: Tone;
};

/** 44×44 round button; an aria-label is required. */
export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  function IconButton({ tone, className, type = "button", ...rest }, ref) {
    return (
      <button
        ref={ref}
        type={type}
        className={iconButtonClassName(tone, className)}
        {...rest}
      />
    );
  },
);

type IconLinkProps = Omit<React.ComponentProps<typeof Link>, "aria-label"> & {
  "aria-label": string;
  tone?: Tone;
};

export function IconLink({ tone, className, ...rest }: IconLinkProps) {
  return <Link className={iconButtonClassName(tone, className)} {...rest} />;
}
