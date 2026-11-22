"use client";

import { useEffect } from "react";
import { Icon } from "./Icons";

export default function Modal({
  onClose,
  variant = "snow",
  label,
  wide,
  children,
}: {
  onClose: () => void;
  variant?: "snow" | "water";
  label: string;
  wide?: boolean;
  children: React.ReactNode;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal modal--${variant}${wide ? " modal--wide" : ""}`} role="dialog" aria-modal="true" aria-label={label}>
        <button className="modal-x" onClick={onClose} aria-label="Close">
          <Icon.close />
        </button>
        {children}
      </div>
    </div>
  );
}
