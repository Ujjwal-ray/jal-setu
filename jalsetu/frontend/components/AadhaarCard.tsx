"use client";

import { useEffect, useState } from "react";
import { api, type AadhaarCheck } from "@/lib/api";
import { ago } from "@/lib/format";
import { shrinkImage } from "@/lib/image";
import { useApp } from "./AppProvider";
import { Icon } from "./Icons";

const MY_AADHAAR = "https://myaadhaar.uidai.gov.in/";

/** On the supplier dashboard: the shop's owner sends a masked Aadhaar, then sees whether an admin has checked it.
 *  The backend (aadhaar.py) deletes the picture once an admin decides, and never stores the full number. */
export default function AadhaarCard({ verified }: { verified: boolean }) {
  const { user, toast } = useApp();
  const [check, setCheck] = useState<AadhaarCheck | null | undefined>(undefined); // undefined while loading
  const [again, setAgain] = useState(false); // still waiting, but the owner wants to send a different picture
  const [name, setName] = useState(user?.name || "");
  const [last4, setLast4] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api<AadhaarCheck | null>("/my-aadhaar")
      .then(setCheck)
      .catch((e) => toast(e.message));
  }, [toast]);

  // show the chosen picture, so the owner can see that only the last 4 digits can be read
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => {
      URL.revokeObjectURL(url);
      setPreview(null);
    };
  }, [file]);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    if (!file) return setErr("Choose a picture of the masked Aadhaar");
    setBusy(true);
    try {
      const form = new FormData();
      form.set("name", name);
      form.set("last4", last4);
      form.set("consent", consent ? "yes" : "");
      form.set("image", await shrinkImage(file), "aadhaar.jpg");
      setCheck(await api<AadhaarCheck>("/my-aadhaar", { method: "POST", form }));
      setAgain(false);
      setFile(null);
      setConsent(false);
      toast("Sent. An admin will check it soon");
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (check === undefined) return null;

  if (check?.status === "approved") {
    return (
      <section className="aadhaar glass" aria-labelledby="aadhaar-title">
        <h2 id="aadhaar-title" className="dash-h">
          Owner&apos;s Aadhaar <span className="verified"><Icon.check width={16} height={16} /> Checked</span>
        </h2>
        <p>
          {check.name} · XXXX XXXX {check.last4}. The picture you sent has been deleted.
        </p>
      </section>
    );
  }

  const showForm = !check || check.status === "rejected" || again;
  return (
    <section className="aadhaar glass" aria-labelledby="aadhaar-title">
      <h2 id="aadhaar-title" className="dash-h">
        Owner&apos;s Aadhaar{" "}
        {check?.status === "pending" && <span className="status-pill status-pill--wait">Waiting for an admin</span>}
        {check?.status === "rejected" && <span className="status-pill status-pill--bad">Not accepted</span>}
      </h2>

      {check?.status === "pending" && !again && (
        <>
          <p>
            Sent {ago(check.submitted)} for {check.name} (XXXX XXXX {check.last4}). An admin will look at it soon.
            {verified ? " Your shop stays verified meanwhile." : " Once it's approved, they can verify your shop and customers will find you."}
          </p>
          <button type="button" className="link-btn" onClick={() => setAgain(true)}>Send a different picture</button>
        </>
      )}

      {check?.status === "rejected" && (
        <p className="aadhaar-reason" role="status">
          <b>Why:</b> {check.note.replace(/\.$/, "")}. Please send it again.
        </p>
      )}

      {showForm && (
        <form className="aadhaar-form" onSubmit={send}>
          <p>
            {verified
              ? "Your shop was verified before JalSetu started checking who runs each shop. Please send your Aadhaar too: if your shop is ever hidden, it needs one to come back. "
              : "Before customers can see your shop, JalSetu checks who runs it. "}
            Send a picture of your <b>masked Aadhaar</b>: it
            hides the first 8 digits and shows only the last 4. You can download it free from the{" "}
            <a href={MY_AADHAAR} target="_blank" rel="noopener noreferrer">myAadhaar website</a> (choose &quot;masked
            Aadhaar&quot;), then send a screenshot or photo of it. <b>Never send a picture that shows all 12 digits.</b>
          </p>
          <label className="wf-label" htmlFor="ad-name">Name, exactly as on the Aadhaar</label>
          <input id="ad-name" className="wf-input" value={name} maxLength={80} onChange={(e) => setName(e.target.value)} required />
          <label className="wf-label" htmlFor="ad-last4">Last 4 digits of the Aadhaar number</label>
          <input
            id="ad-last4"
            className="wf-input wf-input--sm wf-input--code"
            inputMode="numeric"
            autoComplete="off"
            maxLength={4}
            pattern="\d{4}"
            title="4 digits"
            value={last4}
            onChange={(e) => setLast4(e.target.value.replace(/\D/g, ""))}
            required
          />
          <label className="wf-label" htmlFor="ad-file">Picture of the masked Aadhaar</label>
          <input
            id="ad-file"
            className="aadhaar-file"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            required
          />
          {preview &&<img className="aadhaar-preview" src={preview} alt="The picture you chose" />}
          <label className="aadhaar-consent">
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} required />
            <span>
              I agree that JalSetu may look at this picture to check who runs this shop. It is deleted as soon as it has been
              checked; only the name and the last 4 digits are kept.
            </span>
          </label>
          {err && <p className="form-err" role="alert">{err}</p>}
          <div className="aadhaar-actions">
            <button type="submit" className="pill pill--navy" disabled={busy}>{busy ? "Sending…" : "Send for checking"}</button>
            {again && <button type="button" className="pill pill--ghost" onClick={() => setAgain(false)}>Cancel</button>}
          </div>
        </form>
      )}
    </section>
  );
}
