"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type ShopDay } from "@/lib/api";
import { clockText } from "@/lib/format";
import { usePoll } from "@/lib/usePoll";
import { useApp } from "./AppProvider";
import Modal from "./Modal";
import RoundButton from "./RoundButton";

type Action = "open" | "close";
const stock = (v: 0 | 1 | null) => (v ? "in stock" : "out of stock");

/** On the supplier dashboard: open the shop when work starts and close it at the end of the day. Each time the
 *  supplier types their password and says whether they have jars in stock. Customers can only order while the
 *  shop is open; a shop left open closes by itself at midnight (backend/shop_hours.py). */
export default function ShopToday({ verified, onStock }: { verified: boolean; onStock: (inStock: boolean) => void }) {
  const { toast } = useApp();
  const [day, setDay] = useState<ShopDay | null>(null);
  const [asking, setAsking] = useState<Action | null>(null);

  const load = useCallback((quiet = false) => {
    return api<ShopDay | null>("/my-shop")
      .then(setDay)
      .catch((e) => !quiet && toast(e.message));
  }, [toast]);
  useEffect(() => {
    void load();
  }, [load]);
  // look again every minute, so a dashboard left open overnight shows the midnight closing
  usePoll(() => load(true), 60_000);

  if (!day) return null;
  const now = day.today.at(-1);

  function done(d: ShopDay, action: Action, inStock: boolean) {
    setDay(d);
    setAsking(null);
    onStock(inStock);
    toast(action === "close" ? "Your shop is closed. Customers can't order until you open it again"
      : inStock ? "Your shop is open. Customers can send you requests" : "Your shop is open, marked out of stock");
  }

  return (
    <section className={"shop-day glass" + (day.open ? " shop-day--open" : "")} aria-labelledby="shop-title">
      <div className="shop-day-main">
        <h2 id="shop-title" className="dash-h">
          Your shop today{" "}
          <span className={"status-pill " + (day.open ? "status-pill--ok" : "status-pill--na")}>{day.open ? "Open" : "Closed"}</span>
        </h2>
        {day.open && now ? (
          <p>
            Open since <b>{clockText(now.opened)}</b>, {stock(now.open_stock)} when you opened. Customers can send you requests.
            Close the shop when you finish for the day.
          </p>
        ) : verified ? (
          <p>Customers can see your shop, but they can&apos;t order until you open it. Open it each day when you start work.</p>
        ) : (
          <p>You can open your shop once an admin has checked your Aadhaar and verified your listing.</p>
        )}
        {day.left_open_last_night && (
          <p className="shop-day-warn">Your shop was left open last night, so it closed by itself at midnight. Please close it each day when you finish.</p>
        )}
        {day.today.length > 0 && (
          <ul className="shop-day-log" aria-label="Today's openings and closings">
            {day.today.map((t) => (
              <li key={t.opened}>
                Opened {clockText(t.opened)} ({stock(t.open_stock)})
                {t.closed && <> · closed {clockText(t.closed)} ({stock(t.close_stock)})</>}
              </li>
            ))}
          </ul>
        )}
      </div>
      {(verified || day.open) && (
        <button className={"pill " + (day.open ? "pill--danger" : "pill--ok")} onClick={() => setAsking(day.open ? "close" : "open")}>
          {day.open ? "Close shop" : "Open shop"}
        </button>
      )}
      {asking && <OpenClose action={asking} onClose={() => setAsking(null)} onDone={(d, inStock) => done(d, asking, inStock)} />}
    </section>
  );
}

/** Asks whether there are jars in stock, and for the password again, before opening or closing the shop. */
function OpenClose({ action, onClose, onDone }: { action: Action; onClose: () => void; onDone: (d: ShopDay, inStock: boolean) => void }) {
  const [inStock, setInStock] = useState<boolean | null>(null);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const opening = action === "open";

  async function send(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    if (inStock === null) return setErr(opening ? "Say whether you have jars in stock" : "Say whether any jars are left in stock");
    setBusy(true);
    try {
      onDone(await api<ShopDay>(`/my-shop/${action}`, { method: "POST", body: { password, in_stock: inStock } }), inStock);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const title = opening ? "Open your shop" : "Close your shop";
  return (
    <Modal onClose={onClose} variant="water" label={title}>
      <form className="water-form water-form--modal" onSubmit={send}>
        <h2 className="modal-title">{title}</h2>
        <p className="modal-note">
          {opening ? "Once it's open, customers can send you requests." : "Customers won't be able to order until you open again."}
        </p>
        <span className="wf-label" id="oc-stock">{opening ? "Do you have jars in stock right now?" : "Are any jars left in stock?"}</span>
        <div className="chips" role="radiogroup" aria-labelledby="oc-stock">
          {([true, false] as const).map((v) => (
            <button key={String(v)} type="button" role="radio" aria-checked={inStock === v} className={inStock === v ? "on" : ""} onClick={() => setInStock(v)}>
              {v ? "Yes, in stock" : "No, out of stock"}
            </button>
          ))}
        </div>
        <label className="wf-label" htmlFor="oc-pass">Your password, to confirm it&apos;s you</label>
        <input id="oc-pass" className="wf-input" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        {err && <p className="form-err" role="alert">{err}</p>}
        <div className="wf-actions">
          <RoundButton size="md" type="submit" disabled={busy}>{busy ? "…" : opening ? "Open" : "Close"}</RoundButton>
        </div>
      </form>
    </Modal>
  );
}
