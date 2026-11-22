import Link from "next/link";

type Common = { children: React.ReactNode; size?: "sm" | "md" | "lg"; className?: string };

/** The big glossy navy circle button used for every primary action. */
export default function RoundButton(
  props: Common & ({ href: string } | (React.ButtonHTMLAttributes<HTMLButtonElement> & { href?: undefined }))
) {
  const { children, size = "lg", className = "" } = props;
  const cls = `round-btn round-btn--${size} ${className}`;
  if ("href" in props && props.href) {
    return (
      <Link href={props.href} className={cls}>
        <span>{children}</span>
      </Link>
    );
  }
  const { size: _s, className: _c, children: _ch, href: _h, ...rest } = props as Common & React.ButtonHTMLAttributes<HTMLButtonElement> & { href?: undefined };
  return (
    <button type="button" {...rest} className={cls}>
      <span>{children}</span>
    </button>
  );
}
