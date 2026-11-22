import type { OrderStatus, Supplier } from "./api";

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
