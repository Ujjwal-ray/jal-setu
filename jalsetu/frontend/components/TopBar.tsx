"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useApp } from "./AppProvider";
import { Icon, Logo } from "./Icons";

/** Logo, the hanging navy ribbon, and the account menu. Sits over the hero / page banner. */
export default function TopBar({ ribbon }: { ribbon?: React.ReactNode }) {
  const { user, ready, openAuth, signOut } = useApp();
  const [open, setOpen] = useState(false);
  const menu = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => !menu.current?.contains(e.target as Node) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  return (
    <header className="topbar">
      <Link href="/" className="topbar-logo" aria-label="JalSetu home">
        <Logo />
      </Link>
      <div className="ribbon">{ribbon ?? <span>Smart water-jar delivery · Kolkata</span>}</div>
      <div className="topbar-account" ref={menu}>
        {!ready ? null : user ? (
          <>
            <button className="glass-pill" onClick={() => setOpen(!open)} aria-expanded={open} aria-haspopup="menu">
              <span className="avatar">{user.name.slice(0, 1).toUpperCase()}</span>
              <span className="glass-pill-name">{user.name.split(" ")[0]}</span>
              <Icon.chevDown width={16} height={16} />
            </button>
            {open && (
              <div className="menu" role="menu" onClick={() => setOpen(false)}>
                <div className="menu-head">
                  {user.name}
                  <small>{user.role === "user" ? "Customer" : user.role === "supplier" ? "Supplier" : "Admin"} · {user.phone}</small>
                </div>
                <Link role="menuitem" href="/">Find suppliers</Link>
                <Link role="menuitem" href="/requests">My requests</Link>
                {user.role === "supplier" && <Link role="menuitem" href="/supplier">Supplier dashboard</Link>}
                {user.role === "admin" && <Link role="menuitem" href="/admin">Admin · verification</Link>}
                <button role="menuitem" onClick={signOut}>Sign out</button>
              </div>
            )}
          </>
        ) : (
          <button className="glass-pill" onClick={() => openAuth()}>
            <Icon.user width={18} height={18} />
            <span>Sign in</span>
          </button>
        )}
      </div>
    </header>
  );
}
