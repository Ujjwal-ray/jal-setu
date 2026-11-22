import type { Supplier } from "@/lib/api";
import { certNo, rupee } from "@/lib/format";
import { Icon } from "./Icons";

/** A JalSetu verification "certificate" rendered from live supplier data. */
export default function Certificate({ s, zoom = true }: { s: Supplier; zoom?: boolean }) {
  const ok = !!s.verified;
  return (
    <div className={"cert" + (ok ? "" : " cert--pending")}>
      <div className="cert-paper">
        <p className="cert-org">JalSetu · supplier verification system</p>
        <div className="cert-head">
          <span className="cert-seal" aria-hidden="true">
            <Icon.drop width={22} height={22} />
          </span>
          <div>
            <p className="cert-title">{ok ? "Certificate of verification" : "Verification pending"}</p>
            <p className="cert-no">No. {certNo(s.id)}</p>
          </div>
        </div>
        <dl className="cert-fields">
          <dt>Supplier</dt>
          <dd>{s.business_name}</dd>
          <dt>Address</dt>
          <dd>{s.address || "—"}</dd>
          <dt>Service area</dt>
          <dd>{s.service_area || "—"}</dd>
          <dt>Product</dt>
          <dd>
            {s.jar_size || "20 L"} jar · {rupee(s.price)}
          </dd>
          <dt>Rating</dt>
          <dd>{s.rating ? `★ ${s.rating} (${s.review_count})` : "Not rated yet"}</dd>
        </dl>
        <div className="cert-lines" aria-hidden="true">
          <i /><i /><i /><i />
        </div>
        <div className="cert-foot">
          <svg viewBox="0 0 90 30" width="78" height="26" aria-hidden="true">
            <path d="M3 22c8-14 12-14 10-2s6-10 10-8-2 12 4 8 6-12 12-10 2 10 8 8 10-8 16-6 8 4 18 0" fill="none" stroke="#1d4f9a" strokeWidth="1.6" strokeLinecap="round" />
          </svg>
          <span className={"cert-stamp" + (ok ? "" : " cert-stamp--pending")}>{ok ? "Verified" : "Pending"}</span>
        </div>
        {zoom && (
          <span className="cert-zoom" aria-hidden="true">
            <Icon.zoom width={48} height={48} />
          </span>
        )}
      </div>
    </div>
  );
}
