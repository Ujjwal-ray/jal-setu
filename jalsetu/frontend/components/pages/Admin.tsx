"use client";

import { useCallback, useEffect, useState } from "react";
import { api, type Supplier } from "@/lib/api";
import { tel } from "@/lib/format";
import { useApp } from "../AppProvider";
import Certificate from "../Certificate";
import PageShell from "../PageShell";

export default function Admin() {
  const { user, toast } = useApp();
  const [rows, setRows] = useState<Supplier[] | null>(null);

  const load = useCallback(() => {
    api<Supplier[]>("/admin/suppliers").then(setRows).catch((e) => toast(e.message));
  }, [toast]);

  useEffect(() => {
    if (user?.role === "admin") load();
  }, [user, load]);

  async function verify(s: Supplier, v: boolean) {
    try {
      await api(`/admin/suppliers/${s.id}/verify`, { method: "POST", body: { verified: v } });
      toast(v ? `${s.business_name} is now verified` : `${s.business_name} was hidden from customers`);
      load();
    } catch (e) {
      toast((e as Error).message);
    }
  }

  const pending = rows?.filter((r) => !r.verified).length ?? 0;

  return (
    <PageShell title="Supplier verification" sub="Only verified suppliers are shown to customers" roles={["admin"]}>
      {rows && (
        <p className="center admin-sum">
          {rows.length} suppliers · <b>{pending} waiting for verification</b>
        </p>
      )}
      <ul className="admin-grid">
        {rows?.map((s) => (
          <li key={s.id}>
            <Certificate s={s} zoom={false} />
            <div className="admin-actions">
              <a className="pill pill--ghost" href={tel(s.contact)}>Call {s.contact}</a>
              {s.verified ? (
                <button className="pill pill--danger" onClick={() => verify(s, false)}>Unverify</button>
              ) : (
                <button className="pill pill--ok" onClick={() => verify(s, true)}>Verify</button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </PageShell>
  );
}
