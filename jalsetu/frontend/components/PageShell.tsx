"use client";

import { useApp } from "./AppProvider";
import Footer from "./Footer";
import RoundButton from "./RoundButton";
import TopBar from "./TopBar";
import type { Role } from "@/lib/api";

/** Snowy banner + content area used by the signed-in pages. */
export default function PageShell({
  title,
  sub,
  roles,
  children,
}: {
  title: string;
  sub: string;
  roles?: Role[];
  children: React.ReactNode;
}) {
  const { user, ready, openAuth } = useApp();
  const allowed = user && (!roles || roles.includes(user.role));
  return (
    <>
      <TopBar />
      <main>
        <section className="banner">
          <h1 className="headline">{title}</h1>
          <p className="hero-sub">{sub}</p>
        </section>
        <section className="page-body">
          {!ready ? null : allowed ? (
            children
          ) : (
            <div className="gate glass">
              <p>
                {user
                  ? `This page is for ${roles?.map((r) => (r === "user" ? "customers" : r + "s")).join(" and ")}. You're signed in as ${user.role === "user" ? "a customer" : "an " + user.role}.`
                  : "Please sign in to continue."}
              </p>
              {!user && (
                <RoundButton size="md" onClick={() => openAuth()}>
                  Sign in
                </RoundButton>
              )}
            </div>
          )}
        </section>
      </main>
      <Footer plain />
    </>
  );
}
