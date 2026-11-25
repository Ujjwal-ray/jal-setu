"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, type Order, type OrderStatus } from "@/lib/api";
import { rupee, slotText, tel, when } from "@/lib/format";
import { usePoll } from "@/lib/usePoll";
import { useApp } from "../AppProvider";
import { Icon } from "../Icons";
import LiveNote from "../LiveNote";
import Modal from "../Modal";
import PageShell from "../PageShell";
import ReportModal from "../ReportModal";
import RoundButton from "../RoundButton";
import StatusTrack from "../StatusTrack";

const POLL_MS = 15_000; // how often the page checks for status changes while it's open

// what to tell the customer when their supplier moves a request along
const UPDATE: Partial<Record<OrderStatus, (supplier: string) => string>> = {
  accepted: (s) => `${s} accepted your request`,
  out_for_delivery: (s) => `${s} is on the way with your jars`,
  delivered: (s) => `${s} marked your jars delivered`,
  rejected: (s) => `${s} couldn't take your request`,
};

type CheckKey = "on_time" | "quality_ok" | "quantity_ok";
const CHECKS: [CheckKey, string][] = [
  ["on_time", "Did it arrive on time?"],
  ["quality_ok", "Was the water quality good?"],
  ["quantity_ok", "Did you get the right number of jars?"],
];

function RateModal({ order, onClose, onRated }: { order: Order; onClose: () => void; onRated: () => void }) {
  const { toast } = useApp();
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [checks, setChecks] = useState<Record<CheckKey, boolean | null>>({ on_time: null, quality_ok: null, quantity_ok: null });
  const [err, setErr] = useState("");
  async function send(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api(`/suppliers/${order.supplier_id}/reviews`, { method: "POST", body: { order_id: order.id, rating, comment, ...checks } });
      toast("Thanks for rating " + order.business_name);
      onRated();
    } catch (e) {
      setErr((e as Error).message);
    }
  }
  return (
    <Modal onClose={onClose} variant="water" label="Rate supplier">
      <form className="water-form water-form--modal" onSubmit={send}>
        <h2 className="modal-title">Rate {order.business_name}</h2>
        <div className="rate" role="radiogroup" aria-label="Rating">
          {[1, 2, 3, 4, 5].map((n) => (
            <button key={n} type="button" role="radio" aria-checked={rating === n} aria-label={`${n} star${n > 1 ? "s" : ""}`} className={n <= rating ? "on" : ""} onClick={() => setRating(n)}>
              <Icon.star width={36} height={36} />
            </button>
          ))}
        </div>
        {CHECKS.map(([key, question]) => (
          <div key={key} className="yesno">
            <span className="wf-label" id={"q-" + key}>{question}</span>
            <div className="seg" role="radiogroup" aria-labelledby={"q-" + key}>
              {([[true, "Yes"], [false, "No"]] as const).map(([v, label]) => (
                <button key={label} type="button" role="radio" aria-checked={checks[key] === v} className={checks[key] === v ? "on" : ""}
                  onClick={() => setChecks({ ...checks, [key]: checks[key] === v ? null : v })}>
                  {label}
                </button>
              ))}
            </div>
          </div>
        ))}
        <label className="wf-label" htmlFor="rate-c">Anything others should know?</label>
        <textarea id="rate-c" className="wf-input wf-textarea" rows={3} value={comment} onChange={(e) => setComment(e.target.value)} />
        {err && <p className="form-err" role="alert">{err}</p>}
        <div className="wf-actions">
          <RoundButton size="md" type="submit">Send</RoundButton>
        </div>
      </form>
    </Modal>
  );
}

export default function Requests() {
  const { user, toast } = useApp();
  const [rows, setRows] = useState<Order[] | null>(null);
  const [rate, setRate] = useState<Order | null>(null);
  const [report, setReport] = useState<Order | null>(null);
  const [stale, setStale] = useState(false);
  const seen = useRef<Map<number, OrderStatus> | null>(null); // each order's status at the last check

  // Timer refreshes are `quiet`: an error turns the live line red instead of popping up every 15 seconds.
  const load = useCallback(
    (quiet = false) =>
      api<Order[]>("/orders", { timeoutMs: 10_000 })
        .then((rs) => {
          const before = seen.current;
          seen.current = new Map(rs.map((o) => [o.id, o.status]));
          setRows(rs);
          setStale(false);
          // only the supplier's moves are announced; cancelling has its own message
          const moved = before ? rs.filter((o) => before.has(o.id) && before.get(o.id) !== o.status && UPDATE[o.status]) : [];
          const say = moved.length === 1 && UPDATE[moved[0].status];
          if (say) toast(say(moved[0].business_name));
          else if (moved.length > 1) toast(`${moved.length} of your requests were updated`);
        })
        .catch((e) => (quiet ? setStale(true) : toast(e.message))),
    [toast]
  );

  useEffect(() => {
    if (!user) return;
    seen.current = null;
    void load();
  }, [user, load]);

  usePoll(() => load(true), POLL_MS, { enabled: !!user });

  async function cancel(o: Order) {
    try {
      await api("/orders/" + o.id, { method: "PATCH", body: { status: "cancelled" } });
      toast("Request cancelled");
      load();
    } catch (e) {
      toast((e as Error).message);
    }
  }

  return (
    <PageShell title="My requests" sub="Every delivery you have asked for, step by step">
      {!rows ? (
        <p className="muted center">Loading…</p>
      ) : rows.length === 0 ? (
        <div className="gate glass">
          <p>No requests yet. Find a supplier near you and order your first jar.</p>
          <RoundButton size="md" href="/#suppliers">Find</RoundButton>
        </div>
      ) : (
        <>
          <LiveNote stale={stale}>Live · this page updates by itself when your supplier responds</LiveNote>
          <ul className="orders">
            {rows.map((o) => (
              <li key={o.id} className="order glass">
                <img className="order-jar" src="/img/jar.svg" alt="" />
                <div className="order-main">
                  <div className="order-top">
                    <h3>{o.business_name}</h3>
                    <span className="order-total">{rupee(o.total)}</span>
                  </div>
                  <p className="order-meta">
                    {o.qty} {o.qty === 1 ? "jar" : "jars"} · requested {when(o.ts)}
                    {o.slot && <> · wanted {slotText(o.slot)}</>}
                    <br />
                    {o.address}
                  </p>
                  <StatusTrack status={o.status} />
                  <div className="order-actions">
                    <a className="pill pill--navy" href={tel(o.contact)}><Icon.phone width={16} height={16} /> Call supplier</a>
                    {o.status === "pending" && <button className="pill pill--danger" onClick={() => cancel(o)}>Cancel request</button>}
                    {o.status === "delivered" && !o.rated && <button className="pill pill--orange" onClick={() => setRate(o)}><Icon.star width={16} height={16} /> Rate</button>}
                    {o.rated && <span className="status-pill status-pill--ok">Rated</span>}
                    {o.reported ? (
                      <span className="status-pill status-pill--wait">Problem reported</span>
                    ) : (
                      o.status !== "cancelled" && <button className="pill pill--ghost" onClick={() => setReport(o)}>Report a problem</button>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </>
      )}
      <p className="center"><Link className="link-btn" href="/#order">Request another delivery</Link></p>
      {rate && <RateModal order={rate} onClose={() => setRate(null)} onRated={() => { setRate(null); load(); }} />}
      {report && <ReportModal order={report} side="customer" onClose={() => setReport(null)} onSent={() => { setReport(null); load(); }} />}
    </PageShell>
  );
}
