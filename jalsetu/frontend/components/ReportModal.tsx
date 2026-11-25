"use client";

import { useState } from "react";
import { api, type Order, type ReportCategory } from "@/lib/api";
import { CUSTOMER_REPORTS, REPORT_LABEL, SUPPLIER_REPORTS } from "@/lib/format";
import { useApp } from "./AppProvider";
import Modal from "./Modal";
import RoundButton from "./RoundButton";

/** "Report a problem" on one order, for its customer or its supplier. The admin sees it on the admin dashboard. */
export default function ReportModal({
  order,
  side,
  onClose,
  onSent,
}: {
  order: Order;
  side: "customer" | "supplier";
  onClose: () => void;
  onSent: () => void;
}) {
  const { toast } = useApp();
  const options = side === "customer" ? CUSTOMER_REPORTS : SUPPLIER_REPORTS;
  const [category, setCategory] = useState<ReportCategory>(options[0]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function send(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      await api(`/orders/${order.id}/reports`, { method: "POST", body: { category, message } });
      toast("Thanks. An admin will look into it");
      onSent();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onClose} variant="water" label="Report a problem">
      <form className="water-form water-form--modal" onSubmit={send}>
        <h2 className="modal-title">Report a problem</h2>
        <p className="modal-note">
          Request #{order.id} · {side === "customer" ? order.business_name : order.customer}. Only JalSetu admins see this.
        </p>
        <span className="wf-label" id="rp-what">What went wrong?</span>
        <div className="chips" role="radiogroup" aria-labelledby="rp-what">
          {options.map((c) => (
            <button key={c} type="button" role="radio" aria-checked={category === c} className={category === c ? "on" : ""} onClick={() => setCategory(c)}>
              {REPORT_LABEL[c]}
            </button>
          ))}
        </div>
        <label className="wf-label" htmlFor="rp-msg">
          Tell us more {category === "other" ? "" : <small>(optional)</small>}
        </label>
        <textarea id="rp-msg" className="wf-input wf-textarea" rows={3} maxLength={1000} value={message} onChange={(e) => setMessage(e.target.value)} />
        {err && <p className="form-err" role="alert">{err}</p>}
        <div className="wf-actions">
          <RoundButton size="md" type="submit" disabled={busy}>{busy ? "…" : "Send"}</RoundButton>
        </div>
      </form>
    </Modal>
  );
}
