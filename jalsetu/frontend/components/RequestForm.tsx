"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, type Supplier } from "@/lib/api";
import { canOrder, km, rupee } from "@/lib/format";
import { useApp } from "./AppProvider";
import { Icon } from "./Icons";
import RoundButton from "./RoundButton";

const today = () => {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
};

export default function RequestForm({
  suppliers,
  selectedId,
  onSelect,
  locLabel,
}: {
  suppliers: Supplier[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  locLabel: string;
}) {
  const { user, openAuth, toast } = useApp();
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [qty, setQty] = useState(1);
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState<{ id: number; name: string } | null>(null);

  const prefilled = useRef(false);
  useEffect(() => {
    // fill the signed-in user's number once; never fight the user if they clear it
    if (user && !prefilled.current && /^\d{10}$/.test(user.phone)) {
      prefilled.current = true;
      setPhone((p) => p || user.phone);
    }
  }, [user]);

  const open = useMemo(() => suppliers.filter(canOrder), [suppliers]); // open today and in stock
  const sup = open.find((s) => s.id === selectedId) || open[0];
  const total = sup ? (sup.price || 0) * qty + (sup.delivery_charge || 0) : 0;

  async function send() {
    if (!sup) return;
    setBusy(true);
    setErr("");
    try {
      const r = await api<{ id: number }>("/orders", {
        method: "POST",
        body: { supplier_id: sup.id, qty, address, phone, email, slot: [date, time].filter(Boolean).join(" ") },
      });
      setDone({ id: r.id, name: sup.business_name });
      toast("Request sent to " + sup.business_name);
      document.getElementById("order")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    const digits = phone.replace(/\D/g, "").slice(-10);
    if (digits.length !== 10) return setErr("Enter a 10-digit phone number");
    if (!address.trim()) return setErr("Enter the delivery address");
    if (!sup) return setErr("No shop near this area is open with jars in stock right now");
    if (!user) {
      openAuth({ phone: digits, message: "Sign in or create an account to send your request. We'll send it right after.", onDone: () => void send() });
      return;
    }
    void send();
  }

  return (
    <section className="water" id="order" aria-labelledby="order-title">
      <div className="water-bg" aria-hidden="true">
        <div className="water-column" />
      </div>
      {done ? (
        <div className="water-form water-done">
          <span className="done-check"><Icon.check width={46} height={46} /></span>
          <h2 id="order-title" className="wf-title">Request sent!</h2>
          <p className="wf-label">
            <b>{done.name}</b> will confirm your delivery soon. You can follow every step in My requests.
          </p>
          <Link className="pill pill--light" href="/requests">View my requests</Link>
          <button className="link-btn link-btn--light" onClick={() => setDone(null)}>Send another request</button>
        </div>
      ) : (
        <form id="request-form" className="water-form" onSubmit={submit} noValidate>
          <h2 id="order-title" className="sr-only">Request a water jar delivery</h2>

          <label className="wf-label" htmlFor="rf-sup">Choose a supplier near {locLabel}</label>
          <div className="wf-select">
            <select id="rf-sup" className="wf-input" value={sup?.id ?? ""} onChange={(e) => onSelect(Number(e.target.value))} disabled={!open.length}>
              {!open.length && <option value="">No shop here is open with jars in stock right now</option>}
              {open.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.business_name} · {rupee(s.price)} {s.distance_km != null ? "· " + km(s.distance_km) : ""}
                </option>
              ))}
            </select>
            <Icon.chevDown />
          </div>

          <label className="wf-label" htmlFor="rf-phone">Enter your phone for delivery updates or a call back</label>
          <input id="rf-phone" className="wf-input" inputMode="tel" autoComplete="tel" placeholder="+91 _____ _____" value={phone} onChange={(e) => setPhone(e.target.value)} />

          <label className="wf-label" htmlFor="rf-addr">Enter the delivery address</label>
          <input id="rf-addr" className="wf-input" autoComplete="street-address" placeholder="Flat, building, street" value={address} onChange={(e) => setAddress(e.target.value)} />

          <span className="wf-label" id="rf-when">How many jars, and when should they arrive?</span>
          <div className="wf-row" role="group" aria-labelledby="rf-when">
            <div className="wf-select wf-select--sm">
              <select className="wf-input wf-input--sm" aria-label="Number of jars" value={qty} onChange={(e) => setQty(Number(e.target.value))}>
                {Array.from({ length: 20 }, (_, i) => i + 1).map((n) => (
                  <option key={n} value={n}>{n} {n === 1 ? "jar" : "jars"}</option>
                ))}
              </select>
              <Icon.chevDown />
            </div>
            <input className="wf-input wf-input--sm" type="date" aria-label="Preferred date" min={today()} value={date} onChange={(e) => setDate(e.target.value)} />
            <input className="wf-input wf-input--sm" type="time" aria-label="Preferred time" value={time} onChange={(e) => setTime(e.target.value)} />
          </div>

          <label className="wf-label" htmlFor="rf-mail">
            For offices, hostels &amp; shops
            <br />
            enter e-mail for a bulk quote and contract
          </label>
          <input id="rf-mail" className="wf-input" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />

          {sup && (
            <p className="wf-total" aria-live="polite">
              {qty} × {rupee(sup.price)} {sup.delivery_charge ? `+ ${rupee(sup.delivery_charge)} delivery` : "· free delivery"} = <b>{rupee(total)}</b>
            </p>
          )}
          {err && <p className="form-err" role="alert">{err}</p>}
        </form>
      )}
      {!done && (
        <div className="edge-cta">
          <RoundButton type="submit" form="request-form" disabled={busy}>
            {busy ? "Sending…" : "Order"}
          </RoundButton>
        </div>
      )}
    </section>
  );
}
