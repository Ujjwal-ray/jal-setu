// Thin client for the Flask API. Next.js rewrites /api/* to the backend (see next.config.ts).

export type Role = "user" | "supplier" | "admin";
export type User = { id: number; name: string; phone: string; role: Role };

export type Supplier = {
  id: number;
  user_id: number | null;
  business_name: string;
  lat: number;
  lng: number;
  address: string | null;
  service_area: string | null;
  contact: string | null;
  verified: number;
  price: number | null;
  delivery_charge: number | null;
  availability: number | null;
  jar_size: string | null;
  rating: number | null;
  review_count: number;
  distance_km?: number | null;
  /** when the shop opened today (Unix seconds); null while it's closed. Customers can only order from open shops. */
  open_since: number | null;
};

/** One opening of a supplier's shop today, and its closing (closed: null while still open). */
export type ShopSession = { opened: number; open_stock: 0 | 1; closed: number | null; close_stock: 0 | 1 | null; closed_by: "owner" | "auto" | null };
/** The supplier's own view of today (backend/shop_hours.py). */
export type ShopDay = { open: boolean; today: ShopSession[]; left_open_last_night: boolean };

export type Review = { rating: number; comment: string; ts: number; name: string };
export type SupplierDetail = Supplier & { reviews: Review[] };

export type OrderStatus = "pending" | "accepted" | "out_for_delivery" | "delivered" | "rejected" | "cancelled";
export type Order = {
  id: number;
  user_id: number;
  supplier_id: number;
  qty: number;
  address: string;
  note: string | null;
  phone: string | null;
  slot: string | null;
  email: string | null;
  status: OrderStatus;
  ts: number;
  business_name: string;
  contact: string;
  customer: string;
  customer_phone: string;
  price: number | null;
  delivery_charge: number | null;
  total: number;
  delivered_at: number | null;
  /** the customer has rated this delivery */
  rated: boolean;
  /** the person viewing has an open problem report on this order */
  reported: boolean;
};

export type ReportCategory = "quality" | "quantity" | "late" | "behaviour" | "payment" | "address" | "other";

export type Report = {
  id: number;
  order_id: number;
  by_role: "customer" | "supplier";
  category: ReportCategory;
  message: string;
  status: "open" | "resolved";
  ts: number;
  resolved_ts: number | null;
  reporter: string;
  reporter_phone: string;
  business_name: string;
  supplier_contact: string | null;
  customer: string;
  customer_phone: string;
  order_status: OrderStatus;
  qty: number;
};

/** 1 = yes, 0 = no, null = not answered */
type Check = 0 | 1 | null;
export type AdminReview = {
  id: number;
  order_id: number | null;
  rating: number;
  comment: string;
  ts: number;
  on_time: Check;
  quality_ok: Check;
  quantity_ok: Check;
  customer: string;
  business_name: string;
};

export type AadhaarStatus = "pending" | "approved" | "rejected";
/** A shop owner's Aadhaar check (backend/aadhaar.py). `note` is the admin's reason when it was rejected. */
export type AadhaarCheck = { status: AadhaarStatus; name: string; last4: string; note: string; submitted: number; decided: number | null };
/** What an admin sees while deciding: the check plus its picture as a data: URL (null once decided). */
export type AadhaarReview = AadhaarCheck & { image: string | null };

export type AdminSupplier = Supplier & {
  aadhaar_status: AadhaarStatus | null;
  aadhaar_name: string | null;
  aadhaar_last4: string | null;
  aadhaar_note: string | null;
  aadhaar_submitted: number | null;
  /** when the owner last closed the shop today, if they did */
  closed_today: number | null;
  /** nights in the last 7 days the shop was left open and closed itself at midnight */
  left_open_nights: number;
  /** when the latest of those openings was */
  last_left_open: number | null;
  owner_name: string | null;
  owner_phone: string | null;
  last_seen: number | null;
  signed_in: boolean;
  online: boolean;
  orders_total: number;
  delivered: number;
  active: number;
  on_the_way: number;
  earned: number;
  on_time_pct: number | null;
  quality_pct: number | null;
  quantity_pct: number | null;
  open_reports: number;
};

/** "info" = fine on your own computer, matters once the site is online. */
export type HealthLevel = "ok" | "info" | "warn" | "bad";
/** The admin's Server health tab (backend/health.py). */
export type AdminHealth = {
  checks: { level: HealthLevel; title: string; detail: string }[];
  /** requests that crashed in the last 7 days, newest first */
  errors: { ts: number; method: string; path: string; error: string }[];
  started: number | null;
  now: number;
};

export type AdminOverview = {
  customers: { total: number; served: number; ordering_now: number };
  orders: { total: number; active: number; by_status: Partial<Record<OrderStatus, number>> };
  money: { earned: number; earned_this_month: number };
  suppliers: {
    accounts: number;
    listed: number;
    verified: number;
    awaiting: number;
    /** verified, open now and in stock */
    in_stock: number;
    open_now: number;
    delivering_now: number;
    busy: number;
    signed_in: number;
    signed_out: number;
    online: number;
  };
  feedback: {
    reviews: number;
    rating: number | null;
    on_time_pct: number | null;
    quality_pct: number | null;
    quantity_pct: number | null;
    reports_total: number;
    reports_open: number;
    reports_open_from_customers: number;
    reports_open_from_suppliers: number;
  };
  online_minutes: number;
  generated_at: number;
};

const TOKEN_KEY = "jstoken";
const USER_KEY = "jsuser";

export function readSession(): { token: string | null; user: User | null } {
  try {
    const token = localStorage.getItem(TOKEN_KEY);
    const user = JSON.parse(localStorage.getItem(USER_KEY) || "null") as User | null;
    return { token, user: token ? user : null };
  } catch {
    return { token: null, user: null };
  }
}

export function writeSession(token: string | null, user: User | null) {
  try {
    if (token && user) {
      localStorage.setItem(TOKEN_KEY, token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
    }
  } catch {
    /* storage blocked: session lasts for this tab only */
  }
}

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

/** `timeoutMs`: give up after this long, so a request stuck on a bad connection can't block the next auto-refresh.
 *  `form`: send a form with a file in it instead of JSON. The browser then writes the Content-Type itself. */
export async function api<T>(path: string, opt: { method?: string; body?: unknown; form?: FormData; timeoutMs?: number } = {}): Promise<T> {
  const { token } = readSession();
  let r: Response;
  try {
    r = await fetch("/api" + path, {
      method: opt.method || "GET",
      headers: { ...(opt.form ? {} : { "Content-Type": "application/json" }), ...(token ? { Authorization: "Bearer " + token } : {}) },
      body: opt.form ?? (opt.body !== undefined ? JSON.stringify(opt.body) : undefined),
      signal: opt.timeoutMs ? AbortSignal.timeout(opt.timeoutMs) : undefined,
    });
  } catch {
    throw new ApiError("Can't reach the JalSetu server. Is the backend running?", 0);
  }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) {
    const fallback = r.status >= 500 ? "Can't reach the JalSetu server. Is the backend running?" : "Request failed";
    throw new ApiError((j as { error?: string }).error || fallback, r.status);
  }
  return j as T;
}

export type Filters = { q: string; maxKm: string; maxPrice: string; sort: "distance" | "price"; available: boolean };
export type Loc = { lat: number; lng: number; label: string };

export function supplierQuery(loc: Loc, f?: Partial<Filters>) {
  const p = new URLSearchParams({ lat: String(loc.lat), lng: String(loc.lng), sort: f?.sort || "distance" });
  if (f?.q) p.set("q", f.q);
  if (f?.maxKm) p.set("max_km", f.maxKm);
  if (f?.maxPrice) p.set("max_price", f.maxPrice);
  if (f?.available) p.set("available", "1");
  return "/suppliers?" + p.toString();
}
