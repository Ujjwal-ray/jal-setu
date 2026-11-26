"use client";

import { useState } from "react";
import { api, type User } from "@/lib/api";
import ForgotPassword from "./ForgotPassword";
import Modal from "./Modal";
import RoundButton from "./RoundButton";
import SignupCode from "./SignupCode";

/** What /register answers: a code was texted (sign-up step 1), or, with phone checks switched off, the new account. */
type RegisterReply = { token?: string; user?: User; delivery?: "sms" | "console" };

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
  const [forgot, setForgot] = useState(false);
  const [name, setName] = useState("");
  const [role, setRole] = useState<"user" | "supplier">("user");
  const [phone, setPhone] = useState(req.phone || "");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [verify, setVerify] = useState<{ testMode: boolean } | null>(null); // sign-up waiting for the texted code

  /** Sign-up step 1, and "Send a new code": the server texts a code, and the box moves on to asking for it. */
  async function startSignup() {
    const j = await api<RegisterReply>("/register", { method: "POST", body: { name, role, phone: phone.trim(), password } });
    if (j.token && j.user) onDone(j.token, j.user); // phone checks are switched off on the server
    else setVerify({ testMode: j.delivery === "console" });
  }

  async function submit(e?: React.FormEvent) {
    e?.preventDefault();
    setErr("");
    setBusy(true);
    try {
      if (register) {
        await startSignup();
      } else {
        const j = await api<{ token: string; user: User }>("/login", { method: "POST", body: { phone: phone.trim(), password } });
        onDone(j.token, j.user);
      }
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onClose} variant="water" label={forgot ? "Reset password" : verify ? "Verify phone" : register ? "Create account" : "Sign in"}>
      {forgot ? (
        <ForgotPassword phone={phone} onBack={() => setForgot(false)} onDone={onDone} />
      ) : verify ? (
        <SignupCode
          phone={phone.trim()}
          testMode={verify.testMode}
          onResend={startSignup}
          onBack={() => setVerify(null)}
          onDone={onDone}
        />
      ) : (
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
          {!register && (
            <button type="button" className="link-btn" onClick={() => { setErr(""); setForgot(true); }}>
              Forgot password?
            </button>
          )}
          <button type="button" className="link-btn" onClick={() => setRegister(!register)}>
            {register ? "I already have an account" : "New here? Create an account"}
          </button>
          {!register && (
            <p className="demo-hint">
              Demo logins: customer <b>9000000001</b> / demo123 · supplier <b>9000000100</b> / supplier123 · admin <b>admin</b> / admin123
            </p>
          )}
        </form>
      )}
    </Modal>
  );
}
