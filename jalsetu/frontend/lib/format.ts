import type { OrderStatus, ReportCategory, Supplier } from "./api";

export const rupee = (n: number | null | undefined) => "₹" + (n ?? 0).toLocaleString("en-IN");

export const km = (d: number | null | undefined) =>
  d == null ? "" : d < 1 ? `${Math.round(d * 1000)} m` : `${d.toFixed(1)} km`;

/** wa.me link for an Indian 10-digit number (adds the 91 country code). */
export function whatsapp(contact: string | null | undefined, text?: string) {
  const digits = (contact || "").replace(/\D/g, "");
  if (digits.length < 10) return null;
  const n = digits.length === 10 ? "91" + digits : digits;
  return `https://wa.me/${n}${text ? "?text=" + encodeURIComponent(text) : ""}`;
}

export const tel = (contact: string | null | undefined) => "tel:" + (contact || "").replace(/[^\d+]/g, "");

/** JalSetu support lines: shown where someone needs a person to help, e.g. a forgotten password. */
export const SUPPORT_PHONES = ["9330427500", "9163717527"];

/** "9330427500" -> "93304 27500", the usual way to write an Indian mobile number. */
export const phoneText = (n: string) => (n.length === 10 ? `${n.slice(0, 5)} ${n.slice(5)}` : n);

export const deliveryText = (s: Pick<Supplier, "delivery_charge">) =>
  s.delivery_charge ? `${rupee(s.delivery_charge)} delivery` : "Free delivery";

export const STATUS_LABEL: Record<OrderStatus, string> = {
  pending: "Requested",
  accepted: "Accepted",
  out_for_delivery: "On the way",
  delivered: "Delivered",
  rejected: "Rejected",
  cancelled: "Cancelled",
};

export const STATUS_STEPS: OrderStatus[] = ["pending", "accepted", "out_for_delivery", "delivered"];

export function when(ts: number) {
  return new Date(ts * 1000).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
}

/** "2026-11-06 18:30" -> "6 Nov, 6:30 pm" (falls back to the raw text). */
export function slotText(slot: string | null | undefined) {
  if (!slot) return "";
  const [d, t] = slot.split(" ");
  const date = /^\d{4}-\d{2}-\d{2}$/.test(d) ? new Date(d + "T" + (t || "00:00")) : null;
  if (!date || isNaN(date.getTime())) return slot;
  const day = date.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  return t ? `${day}, ${date.toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" })}` : day;
}

export const certNo = (id: number) => `JS-2026-${String(id).padStart(4, "0")}`;

/** "just now", "12 min ago", "3 h ago", or the date for anything older than a day. */
export function ago(ts: number | null | undefined) {
  if (!ts) return "never";
  const s = Math.max(0, Date.now() / 1000 - ts);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return when(ts);
}

export const pct = (n: number | null | undefined) => (n == null ? "–" : `${n}%`);

export const REPORT_LABEL: Record<ReportCategory, string> = {
  quality: "Water quality",
  quantity: "Wrong number of jars",
  late: "Late or missed delivery",
  behaviour: "Behaviour",
  payment: "Payment",
  address: "Wrong address / not reachable",
  other: "Something else",
};

/** what each side of an order can report */
export const CUSTOMER_REPORTS: ReportCategory[] = ["quality", "quantity", "late", "behaviour", "payment", "other"];
export const SUPPLIER_REPORTS: ReportCategory[] = ["address", "payment", "behaviour", "other"];
