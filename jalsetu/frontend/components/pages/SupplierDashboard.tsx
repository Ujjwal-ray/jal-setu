"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import { api, type Order, type OrderStatus, type Supplier } from "@/lib/api";
import { rupee, slotText, tel, when } from "@/lib/format";
import { useApp } from "../AppProvider";
import { Icon } from "../Icons";
import PageShell from "../PageShell";
import RoundButton from "../RoundButton";
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

type Form = { business_name: string; contact: string; address: string; service_area: string; price: string; delivery_charge: string; availability: boolean };

export default function SupplierDashboard() {
  const { user, toast } = useApp();
  const [listing, setListing] = useState<Supplier | null | undefined>(undefined);
  const [f, setF] = useState<Form | null>(null);
  const [pin, setPin] = useState<[number, number]>([22.5645, 88.3951]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [l, os] = await Promise.all([api<Supplier | null>("/my-listing"), api<Order[]>("/supplier/orders")]);
      setListing(l);
      setOrders(os);
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

  useEffect(() => {
    if (user?.role === "supplier") void load();
  }, [user, load]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!f) return;
    setBusy(true);
    try {
      const l = await api<Supplier>("/my-listing", { method: "PUT", body: { ...f, lat: pin[0], lng: pin[1] } });
      setListing(l);
      toast(l.verified ? "Listing updated" : "Listing saved — an admin will verify it soon");
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
      void load();
    } catch (e) {
      toast((e as Error).message);
    }
  }

  const set = (p: Partial<Form>) => f && setF({ ...f, ...p });
  const pending = orders.filter((o) => o.status === "pending").length;

  return (
    <PageShell title="Supplier dashboard" sub="Keep your listing fresh and answer delivery requests" roles={["supplier"]}>
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
          {orders.length === 0 ? (
            <div className="gate glass">
              <p>{listing?.verified ? "No requests yet. They will appear here as customers order." : "Once an admin verifies your listing, customers can find you and send requests."}</p>
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
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </PageShell>
  );
}
