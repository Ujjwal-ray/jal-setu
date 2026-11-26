"use client";

import { useEffect, useState } from "react";
import { api, type SupplierDetail } from "@/lib/api";
import { canOrder, clockText, deliveryText, km, rupee, stockText, tel, when, whatsapp } from "@/lib/format";
import { Icon } from "./Icons";
import Modal from "./Modal";
import RoundButton from "./RoundButton";

export default function SupplierModal({
  id,
  distance,
  onClose,
  onOrder,
}: {
  id: number;
  distance?: number | null;
  onClose: () => void;
  onOrder: (id: number) => void;
}) {
  const [s, setS] = useState<SupplierDetail | null>(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api<SupplierDetail>("/suppliers/" + id).then(setS).catch((e) => setErr(e.message));
  }, [id]);

  const wa = s && whatsapp(s.contact, `Hi ${s.business_name}, I found you on JalSetu. I need 20 L water jars.`);

  return (
    <Modal onClose={onClose} label={s?.business_name || "Supplier"} wide>
      {!s ? (
        <p className="modal-loading">{err || "Loading…"}</p>
      ) : (
        <div className="sd">
          <div className="sd-art">
            <img src="/img/jar.svg" alt="" />
          </div>
          <div className="sd-body">
            <h2 className="slide-name">
              {s.business_name}
              <span className="verified"><Icon.check width={16} height={16} /> Verified</span>
            </h2>
            <p className="slide-price">
              {rupee(s.price)}
              <small> / {s.jar_size || "20 L"} jar</small>
            </p>
            <ul className="drop-list">
              <li><span className="drop-badge drop-badge--sm"><Icon.drop /></span>{deliveryText(s)}{distance != null && ` · ${km(distance)} from you`}</li>
              <li><span className="drop-badge drop-badge--sm"><Icon.drop /></span>Serves {s.service_area || "nearby areas"}</li>
              <li><span className="drop-badge drop-badge--sm"><Icon.drop /></span>{s.address || "Address on request"}</li>
              <li>
                <span className="drop-badge drop-badge--sm"><Icon.drop /></span>
                <span className={canOrder(s) ? "ok" : "bad"}>{stockText(s)}</span>
                {s.open_since ? ` · open since ${clockText(s.open_since)}` : " · you can order once the owner opens the shop"}
              </li>
            </ul>
            <div className="slide-actions">
              <RoundButton size="md" disabled={!canOrder(s)} onClick={() => onOrder(s.id)}>Order</RoundButton>
              <div className="slide-links">
                <a className="pill pill--navy" href={tel(s.contact)}><Icon.phone width={16} height={16} /> {s.contact}</a>
                {wa && <a className="pill pill--wa" href={wa} target="_blank" rel="noreferrer"><Icon.chat width={16} height={16} /> WhatsApp</a>}
              </div>
            </div>
          </div>
          <div className="sd-reviews">
            <h3>
              Reviews {s.rating ? <span className="stars">★ {s.rating}</span> : null} <small>({s.review_count})</small>
            </h3>
            {s.reviews.length ? (
              <ul>
                {s.reviews.map((r, i) => (
                  <li key={i}>
                    <span className="stars" aria-label={`${r.rating} out of 5`}>{"★".repeat(r.rating)}<i>{"★".repeat(5 - r.rating)}</i></span>
                    <b>{r.name}</b> <small>{when(r.ts)}</small>
                    {r.comment && <p>{r.comment}</p>}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="muted">No reviews yet. Customers can rate a supplier after a delivered order.</p>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}
