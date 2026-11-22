import type { OrderStatus } from "@/lib/api";
import { STATUS_LABEL, STATUS_STEPS } from "@/lib/format";
import { Icon } from "./Icons";

/** Droplet timeline: Requested → Accepted → On the way → Delivered. */
export default function StatusTrack({ status }: { status: OrderStatus }) {
  if (status === "rejected" || status === "cancelled") {
    return <span className="status-pill status-pill--bad">{STATUS_LABEL[status]}</span>;
  }
  const at = STATUS_STEPS.indexOf(status);
  return (
    <ol className="track" aria-label={`Status: ${STATUS_LABEL[status]}`}>
      {STATUS_STEPS.map((st, i) => (
        <li key={st} className={i <= at ? "done" : ""} aria-current={i === at ? "step" : undefined}>
          <span className="track-dot">{i < at || st === "delivered" && i === at ? <Icon.check width={16} height={16} /> : <Icon.drop width={16} height={16} />}</span>
          <small>{STATUS_LABEL[st]}</small>
        </li>
      ))}
    </ol>
  );
}
