import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Props = {
  variant?: "ghost" | "solid";
  size?: "md" | "sm";
  href?: string;
  external?: boolean;
  children: ReactNode;
  className?: string;
} & Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className">;

/** Landing-page buttons: radius 10px, ghost = hairline border, solid = white with black text. */
export default function Button({ variant = "ghost", size = "md", href, external, children, className = "", ...rest }: Props) {
  const cls = `btn ${variant === "solid" ? "btn-solid" : "btn-ghost"} ${size === "sm" ? "btn-sm" : ""} ${className}`;
  if (href) {
    return external ? (
      <a href={href} className={cls} target="_blank" rel="noreferrer">{children}</a>
    ) : (
      <Link href={href} className={cls}>{children}</Link>
    );
  }
  return <button type="button" className={cls} {...rest}>{children}</button>;
}
