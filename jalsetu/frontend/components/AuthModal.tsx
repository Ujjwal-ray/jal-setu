"use client";

import { useState } from "react";
import { api, type User } from "@/lib/api";
import Modal from "./Modal";
import RoundButton from "./RoundButton";

export type AuthRequest = { phone?: string; message?: string; register?: boolean; onDone?: (u: User) => void };

export default function AuthModal({
  req,
  onClose,
  onDone,
}: {
  req: AuthRequest;
  onClose: () => void;
  onDone: (token: string, user: User) => void;
}) {
  const [register, setRegister] = useState(!!req.register);
  const [name, setName] = useState("");
  const [role, setRole] = useState<"user" | "supplier">("user");
  const [phone, setPhone] = useState(req.phone || "");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function submit(e?: React.FormEvent) {
    e?.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const body: Record<string, string> = { phone: phone.trim(), password };
      if (register) Object.assign(body, { name, role });
      const j = await api<{ token: string; user: User }>(register ? "/register" : "/login", { method: "POST", body });
      onDone(j.token, j.user);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onClose} variant="water" label={register ? "Create account" : "Sign in"}>
      <form className="water-form water-form--modal" onSubmit={submit}>
        <h2 className="modal-title">{register ? "Create your account" : "Sign in to JalSetu"}</h2>
        {req.message && <p className="modal-note">{req.message}</p>}
        {register && (
          <>
            <label className="wf-label" htmlFor="a-name">Your name</label>
            <input id="a-name" className="wf-input" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" required />
            <span className="wf-label">I am a</span>
            <div className="seg" role="radiogroup" aria-label="Account type">
              <button type="button" role="radio" aria-checked={role === "user"} className={role === "user" ? "on" : ""} onClick={() => setRole("user")}>
                Customer
              </button>
              <button type="button" role="radio" aria-checked={role === "supplier"} className={role === "supplier" ? "on" : ""} onClick={() => setRole("supplier")}>
                Supplier
              </button>
            </div>
          </>
        )}
        <label className="wf-label" htmlFor="a-phone">Phone number</label>
        <input id="a-phone" className="wf-input" value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" autoComplete="username" placeholder="10-digit mobile" required />
        <label className="wf-label" htmlFor="a-pass">Password</label>
        <input id="a-pass" className="wf-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete={register ? "new-password" : "current-password"} required />
        {err && <p className="form-err" role="alert">{err}</p>}
        <div className="wf-actions">
          <RoundButton type="submit" disabled={busy} size="md">
            {busy ? "…" : register ? "Create" : "Sign in"}
          </RoundButton>
        </div>
        <button type="button" className="link-btn" onClick={() => setRegister(!register)}>
          {register ? "I already have an account" : "New here? Create an account"}
        </button>
        {!register && (
          <p className="demo-hint">
            Demo logins: customer <b>9000000001</b> / demo123 · supplier <b>9000000100</b> / supplier123 · admin <b>admin</b> / admin123
          </p>
        )}
      </form>
    </Modal>
  );
}
