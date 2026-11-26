"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, type Order, type OrderStatus, type Supplier } from "@/lib/api";
import { chime } from "@/lib/chime";
import { rupee, slotText, tel, when } from "@/lib/format";
import { usePoll } from "@/lib/usePoll";
import AadhaarCard from "../AadhaarCard";
import { useApp } from "../AppProvider";
import { Icon } from "../Icons";
import LiveNote from "../LiveNote";
import PageShell from "../PageShell";
import ReportModal from "../ReportModal";
import RoundButton from "../RoundButton";
import ShopToday from "../ShopToday";
import StatusTrack from "../StatusTrack";

const PinPicker = dynamic(() => import("../SupplierMap").then((m) => m.PinPicker), {
  ssr: false,
  loading: () => <div className="map-loading">Loading map…</div>,
});

const NEXT: Partial<Record<OrderStatus, [OrderStatus, string, string][]>> = {
  pending: [["accepted", "Accept", "pill--navy"], ["rejected", "Reject", "pill--danger"]],
  accepted: [["out_for_delivery", "Out for delivery", "pill--navy"], ["rejected", "Reject", "pill--danger"]],
  out_for_delivery: [["delivered", "Mark delivered", "pill--ok"]],
};

const ACTIVE: OrderStatus[] = ["pending", "accepted", "out_for_delivery"];

const POLL_MS = 15_000; // how often the dashboard checks for new requests

/** Totals for the summary tiles. Earnings count delivered orders only, at the price quoted when each was placed. */
function summarize(orders: Order[]) {
  const monthStart = new Date();
  monthStart.setDate(1);
  monthStart.setHours(0, 0, 0, 0);
  const since = monthStart.getTime() / 1000;
  const delivered = orders.filter((o) => o.status === "delivered");
  const earned = (list: Order[]) => list.reduce((sum, o) => sum + (o.total || 0), 0);
  return {
    received: orders.length,
    delivered: delivered.length,
    jars: delivered.reduce((n, o) => n + o.qty, 0),
    active: orders.filter((o) => ACTIVE.includes(o.status)).length,
    earned: earned(delivered),
    earnedThisMonth: earned(delivered.filter((o) => (o.delivered_at ?? o.ts) >= since)),
  };
}

type Form = { business_name: string; contact: string; address: string; service_area: string; price: string; delivery_charge: string; availability: boolean };

export default function SupplierDashboard() {
  const { user, toast } = useApp();
  const [listing, setListing] = useState<Supplier | null | undefined>(undefined);
  const [f, setF] = useState<Form | null>(null);
  const [pin, setPin] = useState<[number, number]>([22.5645, 88.3951]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<Order | null>(null);
  const [stale, setStale] = useState(false);
  const seen = useRef<Map<number, OrderStatus> | null>(null); // each order's status at the last check

  // The shop details are loaded once, so refreshing the orders never undoes listing edits that aren't saved yet.
  const loadListing = useCallback(async () => {
    try {
      const l = await api<Supplier | null>("/my-listing");
      setListing(l);
      setF((cur) =>
        cur ?? {
          business_name: l?.business_name || "",
          contact: l?.contact || user?.phone || "",
          address: l?.address || "",
          service_area: l?.service_area || "",
          price: String(l?.price ?? 40),
          delivery_charge: String(l?.delivery_charge ?? 0),
          availability: l ? !!l.availability : true,
        }
      );
      if (l) setPin([l.lat, l.lng]);
    } catch (e) {
      toast((e as Error).message);
    }
  }, [toast, user]);

  // Incoming requests: loaded on open, after each action, and every POLL_MS.
  // Timer refreshes are `quiet`: an error turns the live line red instead of popping up every 15 seconds.
  const loadOrders = useCallback(
    async (quiet = false) => {
      try {
        const os = await api<Order[]>("/supplier/orders", { timeoutMs: 10_000 });
        const before = seen.current;
        seen.current = new Map(os.map((o) => [o.id, o.status]));
        setOrders(os);
        setStale(false);
        if (!before) return; // first load: nothing to compare with yet
        const arrived = os.filter((o) => o.status === "pending" && !before.has(o.id));
        const cancelled = os.filter((o) => o.status === "cancelled" && before.has(o.id) && before.get(o.id) !== "cancelled");
        const lines = [
          ...arrived.map((o) => `New request: ${o.customer}, ${o.qty} ${o.qty === 1 ? "jar" : "jars"}`),
          ...cancelled.map((o) => `${o.customer} cancelled their request`),
        ];
        if (lines.length) toast(lines.length > 2 ? `${lines.length} updates to your requests` : lines.join(" · "));
        if (arrived.length) chime();
      } catch (e) {
        if (quiet) setStale(true);
        else toast((e as Error).message);
      }
    },
    [toast]
  );

  useEffect(() => {
    if (user?.role !== "supplier") return;
    seen.current = null;
    void loadListing();
    void loadOrders();
  }, [user, loadListing, loadOrders]);

  // keeps checking while the tab is in the background too, so a new request is never missed
  usePoll(() => loadOrders(true), POLL_MS, { enabled: user?.role === "supplier", background: true });

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!f) return;
    setBusy(true);
    try {
      const l = await api<Supplier>("/my-listing", { method: "PUT", body: { ...f, lat: pin[0], lng: pin[1] } });
      setListing(l);
      toast(l.verified ? "Listing updated" : "Listing saved. An admin will verify it once they've checked your Aadhaar");
    } catch (e) {
      toast((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function move(o: Order, status: OrderStatus) {
    try {
      await api("/orders/" + o.id, { method: "PATCH", body: { status } });
      toast("Request updated");
      void loadOrders();
    } catch (e) {
      toast((e as Error).message);
    }
  }

  const set = (p: Partial<Form>) => f && setF({ ...f, ...p });
  // opening or closing the shop sets the stock, so the listing form mustn't later save its older answer over it
  const setStock = useCallback((inStock: boolean) => {
    setF((cur) => cur && { ...cur, availability: inStock });
    setListing((l) => l && { ...l, availability: inStock ? 1 : 0 });
  }, []);
  const pending = orders.filter((o) => o.status === "pending").length;
  const stats = useMemo(() => summarize(orders), [orders]);
  const loaded = listing !== undefined;

  // "(2) Supplier dashboard · JalSetu": requests waiting for an answer show in the browser tab
  useEffect(() => {
    const strip = (t: string) => t.replace(/^\(\d+\) /, "");
    document.title = (pending ? `(${pending}) ` : "") + strip(document.title);
    return () => {
      document.title = strip(document.title);
    };
  }, [pending]);
  const show = (v: string | number) => (loaded ? v : "–");

  return (
    <PageShell title="Supplier dashboard" sub="Keep your listing fresh and answer delivery requests" roles={["supplier"]}>
      <ul className="stats" aria-label="Your business so far">
        <li className="stat glass">
          <span className="stat-label">Orders received</span>
          <b className="stat-value">{show(stats.received)}</b>
          <span className="stat-sub">since you joined</span>
        </li>
        <li className="stat glass">
          <span className="stat-label">Delivered</span>
          <b className="stat-value">{show(stats.delivered)}</b>
          <span className="stat-sub">{stats.jars} {stats.jars === 1 ? "jar" : "jars"} delivered</span>
        </li>
        <li className="stat glass">
          <span className="stat-label">In progress</span>
          <b className="stat-value">{show(stats.active)}</b>
          <span className="stat-sub">{pending ? `${pending} waiting for your answer` : "nothing waiting"}</span>
        </li>
        <li className="stat stat--money glass">
          <span className="stat-label">Total earned</span>
          <b className="stat-value">{show(rupee(stats.earned))}</b>
          <span className="stat-sub">{rupee(stats.earnedThisMonth)} from this month&apos;s orders</span>
        </li>
      </ul>
      {/* opening the shop and the Aadhaar check belong to a shop, so they appear once the listing has been saved */}
      {listing && <ShopToday verified={!!listing.verified} onStock={setStock} />}
      {listing && <AadhaarCard verified={!!listing.verified} />}
      <div className="dash">
        <section className="water water--card" aria-labelledby="listing-title">
          <div className="water-bg" aria-hidden="true">
            <div className="water-column" />
          </div>
          {f && (
            <form className="water-form" onSubmit={save}>
              <h2 id="listing-title" className="wf-title">
                My listing{" "}
                {listing &&
                  (listing.verified ? (
                    <span className="verified"><Icon.check width={16} height={16} /> Verified</span>
                  ) : (
                    <span className="status-pill status-pill--wait">Awaiting verification</span>
                  ))}
              </h2>
              <label className="wf-label" htmlFor="l-name">Business name</label>
              <input id="l-name" className="wf-input" value={f.business_name} onChange={(e) => set({ business_name: e.target.value })} required />
              <label className="wf-label" htmlFor="l-phone">Contact phone (customers call or WhatsApp this)</label>
              <input id="l-phone" className="wf-input" inputMode="tel" value={f.contact} onChange={(e) => set({ contact: e.target.value })} />
              <label className="wf-label" htmlFor="l-addr">Shop address</label>
              <input id="l-addr" className="wf-input" value={f.address} onChange={(e) => set({ address: e.target.value })} />
              <label className="wf-label" htmlFor="l-area">Areas you deliver to (comma separated)</label>
              <input id="l-area" className="wf-input" value={f.service_area} onChange={(e) => set({ service_area: e.target.value })} />
              <span className="wf-label" id="l-money">Jar price, delivery charge and stock</span>
              <div className="wf-row" role="group" aria-labelledby="l-money">
                <input className="wf-input wf-input--sm" type="number" min={0} aria-label="Jar price in rupees" value={f.price} onChange={(e) => set({ price: e.target.value })} />
                <input className="wf-input wf-input--sm" type="number" min={0} aria-label="Delivery charge in rupees" value={f.delivery_charge} onChange={(e) => set({ delivery_charge: e.target.value })} />
                <div className="wf-select wf-select--sm">
                  <select className="wf-input wf-input--sm" aria-label="Stock" value={f.availability ? "1" : "0"} onChange={(e) => set({ availability: e.target.value === "1" })}>
                    <option value="1">In stock</option>
                    <option value="0">Out of stock</option>
                  </select>
                  <Icon.chevDown />
                </div>
              </div>
              <span className="wf-label">Drag the pin or tap the map to mark your shop</span>
              <div className="pin-map">
                <PinPicker value={pin} onChange={setPin} />
              </div>
              <div className="wf-actions">
                <RoundButton type="submit" size="md" disabled={busy}>{busy ? "…" : "Save"}</RoundButton>
              </div>
            </form>
          )}
        </section>

        <section className="dash-orders" aria-labelledby="in-title">
          <h2 id="in-title" className="dash-h">
            Incoming requests {pending > 0 && <span className="count">{pending} new</span>}
          </h2>
          <LiveNote stale={stale}>Live · new requests appear here by themselves</LiveNote>
          {orders.length === 0 ? (
            <div className="gate glass">
              <p>{listing?.verified ? "No requests yet. They will appear here as customers order." : "Once an admin has checked your Aadhaar and verified your listing, customers can find you and send requests."}</p>
            </div>
          ) : (
            <ul className="orders">
              {orders.map((o) => (
                <li key={o.id} className="order glass">
                  <div className="order-main">
                    <div className="order-top">
                      <h3>{o.customer}</h3>
                      <span className="order-total">{rupee(o.total)}</span>
                    </div>
                    <p className="order-meta">
                      {o.qty} {o.qty === 1 ? "jar" : "jars"} · {when(o.ts)}
                      {o.slot && <> · wanted {slotText(o.slot)}</>}
                      <br />
                      {o.address}
                      {o.email && <><br />Bulk quote to: {o.email}</>}
                      {o.note && <><br />Note: {o.note}</>}
                    </p>
                    <StatusTrack status={o.status} />
                    <div className="order-actions">
                      <a className="pill pill--ghost" href={tel(o.phone || o.customer_phone)}><Icon.phone width={16} height={16} /> {o.phone || o.customer_phone}</a>
                      {(NEXT[o.status] || []).map(([st, label, cls]) => (
                        <button key={st} className={"pill " + cls} onClick={() => move(o, st)}>{label}</button>
                      ))}
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
          )}
        </section>
      </div>
      {report && <ReportModal order={report} side="supplier" onClose={() => setReport(null)} onSent={() => { setReport(null); void loadOrders(); }} />}
    </PageShell>
  );
}
