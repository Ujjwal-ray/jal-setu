"use client";

import { useState } from "react";
import type { Supplier } from "@/lib/api";
import { km, rupee, tel, whatsapp } from "@/lib/format";
import { Icon } from "./Icons";

/** Floating orange-ringed phone button: one tap to reach the nearest open supplier. */
export default function CallFab({ nearest, onFind }: { nearest: Supplier | undefined; onFind: () => void }) {
  const [open, setOpen] = useState(false);
  const wa = nearest && whatsapp(nearest.contact, `Hi ${nearest.business_name}, I need 20 L water jars (via JalSetu).`);
  return (
    <div className="fab-wrap">
      {open && (
        <div className="fab-pop" role="dialog" aria-label="Call the nearest supplier">
          {nearest ? (
            <>
              <small>Nearest open supplier</small>
              <b>{nearest.business_name}</b>
              <span>
                {rupee(nearest.price)} / jar{nearest.distance_km != null ? ` · ${km(nearest.distance_km)}` : ""}
              </span>
              <div className="fab-actions">
                <a className="pill pill--navy" href={tel(nearest.contact)}><Icon.phone width={16} height={16} /> Call</a>
                {wa && <a className="pill pill--wa" href={wa} target="_blank" rel="noreferrer"><Icon.chat width={16} height={16} /> WhatsApp</a>}
              </div>
            </>
          ) : (
            <>
              <b>No open supplier found here</b>
              <button className="pill pill--navy" onClick={() => { setOpen(false); onFind(); }}>Search the map</button>
            </>
          )}
        </div>
      )}
      <button className="fab" onClick={() => setOpen(!open)} aria-expanded={open} aria-label="Call the nearest supplier">
        <Icon.phoneWaves width={34} height={34} />
      </button>
    </div>
  );
}
