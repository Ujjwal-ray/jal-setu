"use client";

import { useState } from "react";
import type { Supplier } from "@/lib/api";
import Certificate from "./Certificate";
import { Icon } from "./Icons";
import RoundButton from "./RoundButton";

export default function Verified({ suppliers, loaded, onOpen, onOrder }: { suppliers: Supplier[]; loaded: boolean; onOpen: (id: number) => void; onOrder: () => void }) {
  const [start, setStart] = useState(0);
  const n = suppliers.length;
  const win = n ? Array.from({ length: Math.min(3, n) }, (_, k) => suppliers[(start + k) % n]) : [];
  const go = (d: number) => n && setStart((start + d + n) % n);

  return (
    <section className="trust" aria-labelledby="trust-title">
      <h2 id="trust-title" className="headline headline--section">
        Verified suppliers,
        <br />
        ratings &amp; reviews
      </h2>
      <div className={"certs certs--" + win.length}>
        {n > 1 && <button className={"arrow arrow--l" + (n <= 3 ? " only-mobile" : "")} onClick={() => go(-1)} aria-label="Previous certificate"><Icon.chevL /></button>}
        {win.map((s, k) => (
          <button key={s.id} data-pos={k} className="cert-btn" onClick={() => onOpen(s.id)} aria-label={`Open ${s.business_name}: details and reviews`}>
            <Certificate s={s} />
            <span className="cert-caption">
              Verification certificate
              <br />«{s.business_name}»
            </span>
          </button>
        ))}
        {n > 1 && <button className={"arrow arrow--r" + (n <= 3 ? " only-mobile" : "")} onClick={() => go(1)} aria-label="Next certificate"><Icon.chevR /></button>}
        {!n && loaded && <p className="muted center">No verified suppliers in this area yet.</p>}
      </div>
      <div className="edge-cta">
        <RoundButton onClick={onOrder}>
          Order
          <br />
          now
        </RoundButton>
      </div>
    </section>
  );
}
