"use client";

import dynamic from "next/dynamic";
import type { Filters, Loc, Supplier } from "@/lib/api";
import { deliveryText, km, rupee, tel, whatsapp } from "@/lib/format";
import { Icon } from "./Icons";
import RoundButton from "./RoundButton";

const SupplierMap = dynamic(() => import("./SupplierMap"), {
  ssr: false,
  loading: () => <div className="map-loading">Loading map…</div>,
});

export default function SupplierShowcase({
  list,
  loading,
  error,
  loc,
  filters,
  setFilters,
  activeId,
  setActiveId,
  onOrder,
  onDetails,
  onPick,
  onLocate,
}: {
  list: Supplier[];
  loading: boolean;
  error: string;
  loc: Loc;
  filters: Filters;
  setFilters: (f: Filters) => void;
  activeId: number | null;
  setActiveId: (id: number) => void;
  onOrder: (id: number) => void;
  onDetails: (id: number) => void;
  onPick: (lat: number, lng: number) => void;
  onLocate: () => void;
}) {
  const idx = Math.max(0, list.findIndex((s) => s.id === activeId));
  const s = list[idx];
  const step = (d: number) => list.length && setActiveId(list[(idx + d + list.length) % list.length].id);
  const set = (p: Partial<Filters>) => setFilters({ ...filters, ...p });
  const wa = s ? whatsapp(s.contact, `Hi ${s.business_name}, I found you on JalSetu. I need 20 L water jars.`) : null;

  return (
    <section className="snow" id="suppliers" aria-labelledby="sup-title">
      <h2 id="sup-title" className="headline headline--section">Suppliers near you</h2>

      <div className="filters glass" role="search">
        <div className="f-loc">
          <Icon.pin className="f-loc-pin" />
          <span>
            <small>Searching near</small>
            {loc.label}
          </span>
          <button className="pill pill--ghost" onClick={onLocate}>
            <Icon.locate width={18} height={18} /> Use my location
          </button>
        </div>
        <label className="f-field f-field--grow">
          <small>Name or area</small>
          <input value={filters.q} placeholder="e.g. Tangra" onChange={(e) => set({ q: e.target.value })} />
        </label>
        <label className="f-field">
          <small>Within</small>
          <select value={filters.maxKm} onChange={(e) => set({ maxKm: e.target.value })}>
            <option value="">Any distance</option>
            {["1", "3", "5", "10"].map((k) => (
              <option key={k} value={k}>{k} km</option>
            ))}
          </select>
        </label>
        <label className="f-field">
          <small>Max price</small>
          <input type="number" min={0} inputMode="numeric" placeholder="₹ any" value={filters.maxPrice} onChange={(e) => set({ maxPrice: e.target.value })} />
        </label>
        <label className="f-field">
          <small>Sort by</small>
          <select value={filters.sort} onChange={(e) => set({ sort: e.target.value as Filters["sort"] })}>
            <option value="distance">Nearest</option>
            <option value="price">Cheapest</option>
          </select>
        </label>
        <label className="f-check">
          <input type="checkbox" checked={filters.available} onChange={(e) => set({ available: e.target.checked })} />
          <span>In stock only</span>
        </label>
      </div>

      <div className="slider" aria-roledescription="carousel" aria-label="Nearby suppliers">
        {list.length > 1 && (
          <>
            <button className="arrow arrow--l" onClick={() => step(-1)} aria-label="Previous supplier"><Icon.chevL /></button>
            <button className="arrow arrow--r" onClick={() => step(1)} aria-label="Next supplier"><Icon.chevR /></button>
          </>
        )}
        {s ? (
          <div className="slide" key={s.id} aria-live="polite">
            <div className="slide-art">
              <img src="/img/jar.svg" alt="20 litre water jar" />
            </div>
            <div className="slide-copy">
              <p className="slide-count">{idx + 1} / {list.length}</p>
              <h3 className="slide-name">
                {s.business_name}
                <span className="verified" title="Verified by JalSetu admin"><Icon.check width={16} height={16} /> Verified</span>
              </h3>
              <p className="slide-price">from {rupee(s.price)}<small> / jar</small></p>
              <p className="slide-desc">
                {s.jar_size || "20 L"} jar · {deliveryText(s)}
                {s.distance_km != null && <> · {km(s.distance_km)} away</>}
                <br />
                Serves {s.service_area || "nearby areas"}.
                <br />
                <span className={s.availability ? "ok" : "bad"}>{s.availability ? "In stock now" : "Out of stock"}</span>
                {" · "}
                {s.rating ? <>★ {s.rating} ({s.review_count} {s.review_count === 1 ? "review" : "reviews"})</> : "No ratings yet"}
              </p>
              <div className="slide-actions">
                <RoundButton size="md" onClick={() => onOrder(s.id)} disabled={!s.availability}>Order</RoundButton>
                <div className="slide-links">
                  <a className="pill pill--navy" href={tel(s.contact)}><Icon.phone width={16} height={16} /> Call</a>
                  {wa && <a className="pill pill--wa" href={wa} target="_blank" rel="noreferrer"><Icon.chat width={16} height={16} /> WhatsApp</a>}
                  <button className="pill pill--ghost" onClick={() => onDetails(s.id)}>Details &amp; reviews</button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="slide slide--empty">
            <div className="slide-art"><img src="/img/jar.svg" alt="" /></div>
            <div className="slide-copy">
              <h3 className="slide-name">{loading ? "Looking for suppliers…" : error ? "Can't load suppliers" : "No suppliers match"}</h3>
              <p className="slide-desc">
                {loading ? "One moment." : error || "Try a wider distance, a higher price limit, or tap another area on the map."}
              </p>
            </div>
          </div>
        )}
      </div>

      <figure className="map-card">
        <div className="map-frame">
          <SupplierMap loc={loc} suppliers={list} activeId={s?.id ?? null} radiusKm={Number(filters.maxKm) || 0} onSelect={setActiveId} onPick={onPick} />
        </div>
        <figcaption className="caption-bar">
          {list.length} {list.length === 1 ? "supplier" : "suppliers"} {filters.maxKm ? `within ${filters.maxKm} km` : "found"} · tap anywhere on the map to search that area
        </figcaption>
      </figure>
    </section>
  );
}
