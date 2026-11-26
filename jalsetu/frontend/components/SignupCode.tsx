"use client";

import { useState } from "react";
import { api, type User } from "@/lib/api";
import RoundButton from "./RoundButton";

/**
 * Sign-up, step 2: the 6-digit code texted to the new account's phone. The account is only created once
 * the code is right, so nobody can sign up with someone else's number.
 */
export default function SignupCode({
  phone,
  testMode,
  onResend,
  onBack,
  onDone,
}: {
  phone: string;
  testMode: boolean;
  onResend: () => Promise<void>;
  onBack: () => void;
  onDone: (token: string, user: User) => void;
}) {
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [note, setNote] = useState("");

  async function attempt(work: () => Promise<void>) {
    setErr("");
    setNote("");
    setBusy(true);
    try {
      await work();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const verify = () =>
    attempt(async () => {
      const j = await api<{ token: string; user: User }>("/register/verify", { method: "POST", body: { phone, code } });
      onDone(j.token, j.user);
    });

  const resend = () =>
    attempt(async () => {
      await onResend();
      setCode("");
      setNote("We sent you a new code. The old one no longer works.");
    });

  return (
    <form className="water-form water-form--modal" onSubmit={(e) => { e.preventDefault(); void verify(); }}>
      <h2 className="modal-title">Check your phone</h2>
      <p className="modal-note">
        We sent a 6-digit code to {phone}. Enter it to finish creating your account. It works for 15 minutes.
      </p>
      {testMode && (
        <p className="demo-hint">Test mode: no SMS service is connected yet, so the code is printed in the terminal running the JalSetu backend.</p>
      )}
      <label className="wf-label" htmlFor="su-code">6-digit code</label>
      <input
        id="su-code"
        className="wf-input wf-input--code"
        value={code}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
        inputMode="numeric"
        autoComplete="one-time-code"
        placeholder="––––––"
        required
      />
      {note && <p className="modal-note" role="status">{note}</p>}
      {err && <p className="form-err" role="alert">{err}</p>}
      <div className="wf-actions">
        <RoundButton type="submit" disabled={busy} size="md">{busy ? "…" : "Verify"}</RoundButton>
      </div>
      <button type="button" className="link-btn" disabled={busy} onClick={() => void resend()}>
        Send a new code
      </button>
      <button type="button" className="link-btn" onClick={onBack}>
        Change number
      </button>
    </form>
  );
}
