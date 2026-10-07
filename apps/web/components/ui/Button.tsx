import Link from "next/link";
import { forwardRef } from "react";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "danger-soft"
  | "ghost"
  | "outline";
export type ButtonSize = "md" | "sm";

const VARIANT: Record<ButtonVariant, string> = {
  primary: "bg-mk-ink-100 text-mk-inverse hover:bg-mk-ink-80",
  secondary: "bg-mk-raised text-mk-ink-100 hover:bg-mk-solid-12",
  "danger-soft": "bg-mk-wrong-soft text-mk-wrong-fg hover:bg-mk-wrong-dot",
  ghost: "bg-transparent text-mk-ink-60 hover:bg-mk-ink-4",
  outline: "border border-mk-ink-12 bg-mk-bg text-mk-ink-100 hover:bg-mk-ink-2",
};

const SIZE: Record<ButtonSize, string> = {
  md: "min-h-[48px] px-6 text-cta",
  sm: "min-h-[44px] px-5 text-[14px] font-medium leading-[14px]",
};

const DISABLED =
  "disabled:cursor-not-allowed disabled:bg-mk-ink-4 disabled:text-mk-ink-44 aria-disabled:cursor-not-allowed aria-disabled:bg-mk-ink-4 aria-disabled:text-mk-ink-44";

export function buttonClassName({
  variant = "primary",
  size = "md",
  className = "",
}: {
  variant?: ButtonVariant;
  size?: ButtonSize;
  className?: string;
}) {
  return `mk-transition inline-flex select-none items-center justify-center gap-2 whitespace-nowrap rounded-button text-center ${SIZE[size]} ${VARIANT[variant]} ${DISABLED} ${className}`;
}

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  function Button(
    { variant, size, className, type = "button", ...rest },
    ref,
  ) {
    return (
      <button
        ref={ref}
        type={type}
        className={buttonClassName({ variant, size, className })}
        {...rest}
      />
    );
  },
);

type ButtonLinkProps = React.ComponentProps<typeof Link> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
};

export function ButtonLink({
  variant,
  size,
  className,
  ...rest
}: ButtonLinkProps) {
  return (
    <Link className={buttonClassName({ variant, size, className })} {...rest} />
  );
}
