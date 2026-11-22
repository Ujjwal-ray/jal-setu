"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api, readSession, writeSession, type User } from "@/lib/api";
import AuthModal, { type AuthRequest } from "./AuthModal";

type Ctx = {
  user: User | null;
  ready: boolean;
  signIn: (token: string, user: User) => void;
  signOut: () => void;
  openAuth: (req?: AuthRequest) => void;
  toast: (msg: string) => void;
};

const AppCtx = createContext<Ctx | null>(null);

export function useApp() {
  const c = useContext(AppCtx);
  if (!c) throw new Error("useApp must be used inside <AppProvider>");
  return c;
}

export default function AppProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [auth, setAuth] = useState<AuthRequest | null>(null);
  const [msg, setMsg] = useState<{ text: string; id: number } | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    const s = readSession();
    setUser(s.user);
    setReady(true);
    if (s.token) {
      // drop a stale token (e.g. after the database was reset)
      api<User>("/me").then(setUser).catch((e) => {
        if (e.status === 401) {
          writeSession(null, null);
          setUser(null);
        }
      });
    }
  }, []);

  const toast = useCallback((text: string) => {
    setMsg({ text, id: Date.now() });
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setMsg(null), 3200);
  }, []);

  const signIn = useCallback((token: string, u: User) => {
    writeSession(token, u);
    setUser(u);
  }, []);

  const signOut = useCallback(() => {
    writeSession(null, null);
    setUser(null);
    toast("Signed out");
  }, [toast]);

  const openAuth = useCallback((req?: AuthRequest) => setAuth(req || {}), []);

  return (
    <AppCtx.Provider value={{ user, ready, signIn, signOut, openAuth, toast }}>
      {children}
      {auth && (
        <AuthModal
          req={auth}
          onClose={() => setAuth(null)}
          onDone={(token, u) => {
            signIn(token, u);
            setAuth(null);
            toast(`Welcome, ${u.name}`);
            auth.onDone?.(u);
          }}
        />
      )}
      <div className={"toast" + (msg ? " show" : "")} role="status" aria-live="polite" key={msg?.id}>
        {msg?.text}
      </div>
    </AppCtx.Provider>
  );
}
