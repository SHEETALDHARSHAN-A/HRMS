import clsx from "clsx"
import { forwardRef } from "react";
import type { ButtonHTMLAttributes, ReactNode } from "react"

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  className?: string;
  variant?: "primary" | "secondary" | "outline" | "ghost";
}

// Use forwardRef for proper DOM handling (e.g., focus)
const Button = forwardRef<HTMLButtonElement, ButtonProps>(({
  children,
  className = "",
  variant = "primary",
  disabled,
  ...rest
}, ref) => {
  const baseStyles =
    "w-auto px-6 py-2 rounded-md text-sm font-medium flex items-center justify-center gap-2 transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed";

  const variants = {
    primary: "bg-[var(--color-primary-500)] text-white hover:bg-[var(--color-primary-600)] shadow-md",
    secondary: "bg-gray-200 text-gray-700 hover:bg-gray-300 shadow-sm",
    outline:
      "border border-gray-300 text-[var(--color-primary-500)] bg-white hover:bg-gray-50 shadow-sm",
    ghost: "text-[var(--color-primary-500)] bg-transparent hover:bg-gray-100",
  };

  return (
    <button
      ref={ref}
      className={clsx(baseStyles, variants[variant], className)}
      disabled={disabled}
      {...rest}
    >
      {children}
    </button>
  );
});

Button.displayName = 'Button';
export default Button;