"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, type Order } from "@/lib/api";
import { rupee, slotText, tel, when } from "@/lib/format";
import { useApp } from "../AppProvider";
import { Icon } from "../Icons";
import Modal from "../Modal";
import PageShell from "../PageShell";
import RoundButton from "../RoundButton";
import StatusTrack from "../StatusTrack";

function RateModal({ order, onClose }: { order: Order; onClose: () => void }) {
  const { toast } = useApp();
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [err, setErr] = useState("");
  async function send(e: React.FormEvent) {
    e.preventDefault();
    try {
      await api(`/suppliers/${order.supplier_id}/reviews`, { method: "POST", body: { rating, comment } });
      toast("Thanks for rating " + order.business_name);
      onClose();
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

  const load = useCallback(() => {
    api<Order[]>("/orders").then(setRows).catch((e) => toast(e.message));
  }, [toast]);

  useEffect(() => {
    if (user) load();
  }, [user, load]);

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
                  {o.status === "delivered" && <button className="pill pill--orange" onClick={() => setRate(o)}><Icon.star width={16} height={16} /> Rate</button>}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="center"><Link className="link-btn" href="/#order">Request another delivery</Link></p>
      {rate && <RateModal order={rate} onClose={() => setRate(null)} />}
    </PageShell>
  );
}
