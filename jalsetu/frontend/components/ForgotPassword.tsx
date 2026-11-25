"use client";

import { useState } from "react";
import { api, type User } from "@/lib/api";
import { phoneText, SUPPORT_PHONES, tel } from "@/lib/format";
import RoundButton from "./RoundButton";

/** Tap-to-call support numbers, for anyone whose SMS doesn't arrive. */
function SupportHint() {
  return (
    <p className="demo-hint support-hint">
      Can&apos;t get the SMS? Call JalSetu support on{" "}
      {SUPPORT_PHONES.map((n, i) => (
        <span key={n}>
          {i > 0 && " or "}
          <a href={tel("+91" + n)}>{phoneText(n)}</a>
        </span>
      ))}
      . Once they&apos;ve checked it&apos;s really you, they can give you a code to enter here.
    </p>
  );
}

/**
 * "Forgot password?" inside the sign-in modal. Step 1 texts a 6-digit code to the account's phone;
 * step 2 takes that code (or one an admin read out) and a new password, then signs the person in.
 */
export default function ForgotPassword({
  phone: startPhone,
  onBack,
  onDone,
}: {
  phone: string;
  onBack: () => void;
  onDone: (token: string, user: User) => void;
}) {
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [phone, setPhone] = useState(startPhone);
  const [sentTo, setSentTo] = useState(""); // empty when the code came from JalSetu support
  const [testMode, setTestMode] = useState(false);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function attempt(work: () => Promise<void>) {
    setErr("");
    setBusy(true);
    try {
      await work();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const sendCode = () =>
    attempt(async () => {
      const r = await api<{ delivery: "sms" | "console" }>("/password/forgot", { method: "POST", body: { phone } });
      setTestMode(r.delivery === "console");
      setSentTo(phone.trim());
      setCode("");
      setStep("code");
    });

  const save = () =>
    attempt(async () => {
      const j = await api<{ token: string; user: User }>("/password/reset", { method: "POST", body: { phone, code, password } });
      onDone(j.token, j.user);
    });

  const back = (
    <button type="button" className="link-btn" onClick={onBack}>
      Back to sign in
    </button>
  );

  if (step === "phone") {
    return (
      <form className="water-form water-form--modal" onSubmit={(e) => { e.preventDefault(); void sendCode(); }}>
        <h2 className="modal-title">Reset your password</h2>
        <p className="modal-note">Enter the mobile number you signed up with. We&apos;ll text you a 6-digit code.</p>
        <label className="wf-label" htmlFor="fp-phone">Phone number</label>
        <input id="fp-phone" className="wf-input" value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" autoComplete="username" placeholder="10-digit mobile" required />
        {err && <p className="form-err" role="alert">{err}</p>}
        <div className="wf-actions">
          <RoundButton type="submit" disabled={busy} size="md">{busy ? "…" : "Send code"}</RoundButton>
        </div>
        <button type="button" className="link-btn" onClick={() => { setErr(""); setSentTo(""); setStep("code"); }}>
          I already have a code
        </button>
        {back}
        <SupportHint />
      </form>
    );
  }

  return (
    <form className="water-form water-form--modal" onSubmit={(e) => { e.preventDefault(); void save(); }}>
      <h2 className="modal-title">Choose a new password</h2>
      <p className="modal-note">
        {sentTo ? `We sent a 6-digit code to ${sentTo}. It works for 15 minutes.` : "Enter the code JalSetu support gave you. It works for 15 minutes."}
      </p>
      {testMode && (
        <p className="demo-hint">Test mode: no SMS service is connected yet, so the code is printed in the terminal running the JalSetu backend.</p>
      )}
      {!sentTo && (
        <>
          <label className="wf-label" htmlFor="fp-phone2">Phone number</label>
          <input id="fp-phone2" className="wf-input" value={phone} onChange={(e) => setPhone(e.target.value)} inputMode="tel" autoComplete="username" placeholder="10-digit mobile" required />
        </>
      )}
      <label className="wf-label" htmlFor="fp-code">6-digit code</label>
      <input
        id="fp-code"
        className="wf-input wf-input--code"
        value={code}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
        inputMode="numeric"
        autoComplete="one-time-code"
        placeholder="––––––"
        required
      />
      <label className="wf-label" htmlFor="fp-pass">New password</label>
      <input id="fp-pass" className="wf-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" minLength={6} placeholder="at least 6 characters" required />
      {err && <p className="form-err" role="alert">{err}</p>}
      <div className="wf-actions">
        <RoundButton type="submit" disabled={busy} size="md">{busy ? "…" : "Save"}</RoundButton>
      </div>
      {sentTo && (
        <button type="button" className="link-btn" disabled={busy} onClick={() => void sendCode()}>
          Send a new code
        </button>
      )}
      {back}
      {sentTo && <SupportHint />}
    </form>
  );
}
