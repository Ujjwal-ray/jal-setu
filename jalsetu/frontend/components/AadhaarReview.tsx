"use client";

import { useEffect, useState } from "react";
import { api, type AadhaarReview as Review, type AdminSupplier } from "@/lib/api";
import { phoneText, when } from "@/lib/format";
import { useApp } from "./AppProvider";
import Modal from "./Modal";

const REASONS = [
  "All 12 digits are showing",
  "The picture is blurry or cut off",
  "The name doesn't match",
  "The last 4 digits don't match",
  "This isn't an Aadhaar",
];

/** Admin: look at the masked Aadhaar a shop's owner sent, then approve or reject it.
 *  Either way the server deletes the picture, so this is the only time anyone sees it. */
export default function AadhaarReview({ s, onClose, onDone }: { s: AdminSupplier; onClose: () => void; onDone: () => void }) {
  const { toast } = useApp();
  const [c, setC] = useState<Review | null>(null);
  const [rejecting, setRejecting] = useState(false);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    api<Review>(`/admin/suppliers/${s.id}/aadhaar`)
      .then(setC)
      .catch((e) => setErr(e.message));
  }, [s.id]);

  async function decide(decision: "approved" | "rejected") {
    if (!c) return;
    setErr("");
    setBusy(true);
    try {
      // `submitted` names the picture shown here: if the owner sent another one meanwhile, the server refuses
      await api(`/admin/suppliers/${s.id}/aadhaar`, { method: "POST", body: { decision, note, submitted: c.submitted } });
      toast(decision === "approved" ? `Aadhaar approved. You can now verify ${s.business_name}` : "Rejected. The supplier will see your reason");
      onDone();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onClose} label="Check the owner's Aadhaar" wide>
      <div className="aadhaar-modal">
        <h2 className="modal-title">Check the owner&apos;s Aadhaar</h2>
        <p className="modal-note">
          <b>{s.business_name}</b> · account of {s.owner_name}
          {s.owner_phone && <>, {phoneText(s.owner_phone)}</>}
        </p>
        {!c ? (
          err ? <p className="form-err" role="alert">{err}</p> : <p className="modal-loading">Loading…</p>
        ) : (
          <>
            <div className="aadhaar-review">
              {c.image ? (
                <img className="aadhaar-photo" src={c.image} alt={`Masked Aadhaar sent by ${s.owner_name ?? "the owner"}`} />
              ) : (
                <p className="gate glass">The picture has already been deleted: this check was decided.</p>
              )}
              <div>
                <dl className="aadhaar-facts">
                  <dt>Name they typed</dt>
                  <dd>{c.name}</dd>
                  <dt>Account name</dt>
                  <dd>{s.owner_name ?? "—"}</dd>
                  <dt>Last 4 digits</dt>
                  <dd>XXXX XXXX {c.last4}</dd>
                  <dt>Sent</dt>
                  <dd>{when(c.submitted)}</dd>
                </dl>
                <p className="aadhaar-rules-h">Approve only if:</p>
                <ul className="aadhaar-rules">
                  <li>only the last 4 digits can be read. If all 12 show, reject it: JalSetu mustn&apos;t keep the full number;</li>
                  <li>the name on it matches the name they typed;</li>
                  <li>its last 4 digits are {c.last4};</li>
                  <li>it looks like a real Aadhaar, not edited.</li>
                </ul>
              </div>
            </div>

            {c.status === "pending" && (rejecting ? (
              <div className="aadhaar-reject">
                <span className="wf-label" id="ar-why">What&apos;s wrong? The supplier will see this.</span>
                <div className="chips" role="group" aria-labelledby="ar-why">
                  {REASONS.map((r) => (
                    <button key={r} type="button" className={note === r ? "on" : ""} aria-pressed={note === r} onClick={() => setNote(r)}>{r}</button>
                  ))}
                </div>
                <textarea className="wf-input wf-textarea" rows={2} maxLength={300} aria-labelledby="ar-why" value={note} onChange={(e) => setNote(e.target.value)} />
                <div className="aadhaar-actions">
                  <button type="button" className="pill pill--danger" disabled={busy || !note.trim()} onClick={() => decide("rejected")}>
                    {busy ? "…" : "Reject"}
                  </button>
                  <button type="button" className="pill pill--ghost" onClick={() => setRejecting(false)}>Back</button>
                </div>
              </div>
            ) : (
              <div className="aadhaar-actions">
                <button type="button" className="pill pill--ok" disabled={busy} onClick={() => decide("approved")}>{busy ? "…" : "Approve"}</button>
                <button type="button" className="pill pill--danger" onClick={() => setRejecting(true)}>Reject…</button>
              </div>
            ))}
            {err && <p className="form-err" role="alert">{err}</p>}
            <p className="muted aadhaar-small">The picture is deleted as soon as you approve or reject it.</p>
          </>
        )}
      </div>
    </Modal>
  );
}
