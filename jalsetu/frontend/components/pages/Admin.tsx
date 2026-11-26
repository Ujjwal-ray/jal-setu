"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, type AdminHealth, type AdminOverview, type AdminReview, type AdminSupplier, type HealthLevel, type Report, type Role } from "@/lib/api";
import { ago, clockText, pct, REPORT_LABEL, rupee, STATUS_LABEL, tel, when } from "@/lib/format";
import AadhaarReview from "../AadhaarReview";
import { useApp } from "../AppProvider";
import Certificate from "../Certificate";
import { Icon } from "../Icons";
import PageShell from "../PageShell";

type Tab = "overview" | "suppliers" | "reports" | "verify" | "help" | "server";
type Feedback = { reports: Report[]; reviews: AdminReview[] };
type ResetCode = { code: string; expires: number; name: string; phone: string; role: Role };

const TABS: [Tab, string][] = [
  ["overview", "Overview"],
  ["suppliers", "Suppliers"],
  ["reports", "Reports & feedback"],
  ["verify", "Verification"],
  ["help", "Password help"],
  ["server", "Server health"],
];
const LEVEL_LABEL: Record<HealthLevel, string> = { ok: "OK", info: "Note", warn: "Check", bad: "Fix now" };
const clock = (ms: number) => new Date(ms).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
const REFRESH_MS = 30_000;
const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? "" : "s"}`;

function Tile({ label, value, sub, tone }: { label: string; value: React.ReactNode; sub?: React.ReactNode; tone?: "money" | "alert" }) {
  return (
    <li className={"stat glass" + (tone ? " stat--" + tone : "")}>
      <span className="stat-label">{label}</span>
      <b className="stat-value">{value}</b>
      {sub && <span className="stat-sub">{sub}</span>}
    </li>
  );
}

function Overview({ o }: { o: AdminOverview }) {
  const { customers: c, suppliers: s, feedback: f } = o;
  const waiting = o.orders.by_status.pending || 0;
  return (
    <>
      <h2 className="admin-h">Customers &amp; orders</h2>
      <ul className="stats">
        <Tile label="Customers served" value={c.served} sub={`got a delivery · ${c.total} registered`} />
        <Tile label="Ordering right now" value={c.ordering_now} sub={`${plural(o.orders.active, "open request")} · ${waiting} not accepted yet`} />
        <Tile label="Delivered orders" value={o.orders.by_status.delivered || 0} sub={`of ${plural(o.orders.total, "request")} in total`} />
        <Tile label="Earned by suppliers" value={rupee(o.money.earned)} sub={`${rupee(o.money.earned_this_month)} this month`} tone="money" />
      </ul>

      <h2 className="admin-h">Suppliers</h2>
      <ul className="stats">
        <Tile label="Delivering right now" value={s.delivering_now} sub={`with jars on the way · ${s.busy} handling orders`} />
        <Tile label="Open for orders" value={s.in_stock} sub={`open now and in stock · ${s.open_now} open in all · ${s.awaiting} awaiting verification`} />
        <Tile label="Online now" value={s.online} sub={`used the site in the last ${o.online_minutes} min`} />
        <Tile label="Signed in" value={s.signed_in} sub={`${s.signed_out} signed out · ${plural(s.accounts, "supplier account")}`} />
      </ul>

      <h2 className="admin-h">Feedback</h2>
      <ul className="stats">
        <Tile label="Average rating" value={f.rating ? `★ ${f.rating}` : "–"} sub={plural(f.reviews, "review")} />
        <Tile label="Delivered on time" value={pct(f.on_time_pct)} sub="customers who said yes" />
        <Tile label="Water quality OK" value={pct(f.quality_pct)} sub={`right number of jars: ${pct(f.quantity_pct)}`} />
        <Tile label="Open reports" value={f.reports_open} tone={f.reports_open ? "alert" : undefined}
          sub={`${f.reports_open_from_customers} from customers · ${f.reports_open_from_suppliers} from suppliers`} />
      </ul>
    </>
  );
}

function Presence({ s }: { s: AdminSupplier }) {
  const [state, label] = s.online ? ["online", "Online now"] : s.signed_in ? ["idle", "Signed in"] : ["off", "Signed out"];
  return (
    <span className={"presence presence--" + state}>
      <i aria-hidden="true" />
      {label}
      <small>last seen {ago(s.last_seen)}</small>
    </span>
  );
}

/** Today's opening and closing, and nights the shop was left open (it then closed itself at midnight). */
function ShopHours({ s }: { s: AdminSupplier }) {
  return (
    <>
      {s.open_since ? (
        <span className="status-pill status-pill--ok">Open since {clockText(s.open_since)}</span>
      ) : s.closed_today ? (
        <span className="status-pill status-pill--na">Closed at {clockText(s.closed_today)}</span>
      ) : (
        <span className="status-pill status-pill--na">Not opened today</span>
      )}
      <small>{s.open_since ? (s.availability ? "in stock" : "out of stock") : s.availability ? "in stock at closing" : "out of stock"}</small>
      {s.left_open_nights > 0 && (
        <small className="bad">
          Left open overnight {s.left_open_nights === 1 ? "once" : `${s.left_open_nights} times`} this week
          {s.last_left_open && <> (last: {new Date(s.last_left_open * 1000).toLocaleDateString("en-IN", { day: "numeric", month: "short" })})</>}
        </small>
      )}
    </>
  );
}

function SupplierTable({ rows }: { rows: AdminSupplier[] }) {
  const sorted = [...rows].sort((a, b) => Number(b.online) - Number(a.online) || b.earned - a.earned);
  return (
    <>
      <h2 className="admin-h">Every supplier · who is online, what they earned, what customers say</h2>
      <div className="table-wrap glass">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Supplier</th>
              <th>Status</th>
              <th>Shop today</th>
              <th>Orders</th>
              <th className="num">Earned</th>
              <th>Customer feedback</th>
              <th className="num">Open reports</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((s) => (
              <tr key={s.id}>
                <td>
                  <b>{s.business_name}</b>
                  <small>{s.owner_name} · <a href={tel(s.contact)}>{s.contact}</a></small>
                  <small>{s.verified ? "Verified" : "Awaiting verification"}</small>
                </td>
                <td><Presence s={s} /></td>
                <td><ShopHours s={s} /></td>
                <td>
                  {plural(s.orders_total, "order")}
                  <small>{s.delivered} delivered · {s.active} in progress{s.on_the_way ? ` (${s.on_the_way} on the way)` : ""}</small>
                </td>
                <td className="num money">{rupee(s.earned)}</td>
                <td>
                  {s.rating ? <>★ {s.rating} <span className="muted">({s.review_count})</span></> : <span className="muted">No ratings yet</span>}
                  <small>On time {pct(s.on_time_pct)} · quality {pct(s.quality_pct)} · quantity {pct(s.quantity_pct)}</small>
                </td>
                <td className="num">{s.open_reports ? <span className="status-pill status-pill--bad">{s.open_reports}</span> : "0"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

function Check({ v, label }: { v: 0 | 1 | null; label: string }) {
  if (v == null) return <li className="check check--na">{label}: not answered</li>;
  return <li className={"check " + (v ? "check--yes" : "check--no")}>{v ? "✓" : "✗"} {label}</li>;
}

function Reports({ fb, onChange }: { fb: Feedback; onChange: () => void }) {
  const { toast } = useApp();
  const [show, setShow] = useState<"open" | "resolved">("open");
  const count = (st: Report["status"]) => fb.reports.filter((r) => r.status === st).length;
  const list = fb.reports.filter((r) => r.status === show);

  async function setStatus(r: Report, status: Report["status"]) {
    try {
      await api(`/admin/reports/${r.id}`, { method: "PATCH", body: { status } });
      toast(status === "resolved" ? "Report marked resolved" : "Report reopened");
      onChange();
    } catch (e) {
      toast((e as Error).message);
    }
  }

  return (
    <>
      <div className="admin-bar">
        <h2 className="admin-h">Problem reports</h2>
        <div className="seg" role="radiogroup" aria-label="Show reports">
          {(["open", "resolved"] as const).map((st) => (
            <button key={st} type="button" role="radio" aria-checked={show === st} className={show === st ? "on" : ""} onClick={() => setShow(st)}>
              {st === "open" ? "Open" : "Resolved"} ({count(st)})
            </button>
          ))}
        </div>
      </div>
      {list.length === 0 ? (
        <div className="gate glass">
          <p>{show === "open" ? "No open reports right now." : "No resolved reports yet."}</p>
        </div>
      ) : (
        <ul className="reports">
          {list.map((r) => (
            <li key={r.id} className="report glass">
              <div className="report-head">
                <span className="tag">{REPORT_LABEL[r.category] ?? r.category}</span>
                <span>From {r.by_role} <b>{r.reporter}</b></span>
                <small>{ago(r.ts)}</small>
              </div>
              {r.message && <p className="report-msg">{r.message}</p>}
              <p className="report-meta">
                Request #{r.order_id} · {plural(r.qty, "jar")} · {STATUS_LABEL[r.order_status]} · supplier <b>{r.business_name}</b> · customer <b>{r.customer}</b>
                {r.status === "resolved" && r.resolved_ts && <> · resolved {ago(r.resolved_ts)}</>}
              </p>
              <div className="order-actions">
                <a className="pill pill--ghost" href={tel(r.customer_phone)}><Icon.phone width={16} height={16} /> Customer</a>
                <a className="pill pill--ghost" href={tel(r.supplier_contact)}><Icon.phone width={16} height={16} /> Supplier</a>
                {r.status === "open" ? (
                  <button className="pill pill--ok" onClick={() => setStatus(r, "resolved")}>Mark resolved</button>
                ) : (
                  <button className="pill pill--ghost" onClick={() => setStatus(r, "open")}>Reopen</button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      <h2 className="admin-h">Latest reviews</h2>
      {fb.reviews.length === 0 ? (
        <div className="gate glass"><p>No reviews yet. Customers rate a supplier after a delivery.</p></div>
      ) : (
        <ul className="reports">
          {fb.reviews.map((rv) => (
            <li key={rv.id} className="report glass">
              <div className="report-head">
                <span className="stars" aria-label={`${rv.rating} out of 5`}>{"★".repeat(rv.rating)}<i>{"★".repeat(5 - rv.rating)}</i></span>
                <span><b>{rv.customer}</b> rated <b>{rv.business_name}</b></span>
                <small>{ago(rv.ts)}</small>
              </div>
              <ul className="checks">
                <Check v={rv.on_time} label="On time" />
                <Check v={rv.quality_ok} label="Water quality" />
                <Check v={rv.quantity_ok} label="Right quantity" />
              </ul>
              {rv.comment && <p className="report-msg">{rv.comment}</p>}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

/** Where the owner's Aadhaar check stands. A shop can only be verified once it's approved. */
function AadhaarLine({ s }: { s: AdminSupplier }) {
  switch (s.aadhaar_status) {
    case "approved":
      return <span className="status-pill status-pill--ok">Aadhaar checked · XXXX {s.aadhaar_last4}</span>;
    case "pending":
      return <span className="status-pill status-pill--wait">Aadhaar waiting for you</span>;
    case "rejected":
      return <span className="status-pill status-pill--bad" title={s.aadhaar_note ?? undefined}>Aadhaar rejected · waiting for a new one</span>;
    default:
      return <span className="status-pill status-pill--na">{s.verified ? "Verified before Aadhaar checks" : "Aadhaar not sent yet"}</span>;
  }
}

function Verification({ rows, onVerify, onChange }: { rows: AdminSupplier[]; onVerify: (s: AdminSupplier, v: boolean) => void; onChange: () => void }) {
  const [review, setReview] = useState<AdminSupplier | null>(null);
  const pending = rows.filter((r) => !r.verified).length;
  const toCheck = rows.filter((r) => r.aadhaar_status === "pending").length;
  // Aadhaar waiting for a decision first; otherwise keep the server's order (unverified first)
  const sorted = [...rows].sort((a, b) => Number(b.aadhaar_status === "pending") - Number(a.aadhaar_status === "pending"));
  return (
    <>
      <p className="center admin-sum">
        {plural(rows.length, "supplier")} · <b>{pending} waiting for verification</b>
        {toCheck > 0 && <> · <b>{plural(toCheck, "Aadhaar check")} waiting</b></>}. A shop can be verified once you&apos;ve checked its
        owner&apos;s Aadhaar. Only verified suppliers are shown to customers.
      </p>
      <ul className="admin-grid">
        {sorted.map((s) => (
          <li key={s.id}>
            <Certificate s={s} zoom={false} />
            <AadhaarLine s={s} />
            <div className="admin-actions">
              <a className="pill pill--ghost" href={tel(s.contact)}>Call {s.contact}</a>
              {s.aadhaar_status === "pending" && (
                <button className="pill pill--navy" onClick={() => setReview(s)}>Check Aadhaar</button>
              )}
              {s.verified ? (
                <button className="pill pill--danger" onClick={() => onVerify(s, false)}>Unverify</button>
              ) : (
                s.aadhaar_status === "approved" && <button className="pill pill--ok" onClick={() => onVerify(s, true)}>Verify</button>
              )}
            </div>
          </li>
        ))}
      </ul>
      {review && (
        <AadhaarReview
          s={review}
          onClose={() => setReview(null)}
          onDone={() => {
            setReview(null);
            onChange();
          }}
        />
      )}
    </>
  );
}

/** Is the backend healthy: database, disk, crashes, SMS, risky settings (backend/health.py). */
function ServerHealth({ h }: { h: AdminHealth | null }) {
  const monitorUrl = (typeof window === "undefined" ? "" : window.location.origin) + "/api/health";
  return (
    <>
      {!h ? (
        <div className="gate glass"><p>Can&apos;t get the server&apos;s health right now. If the red bar above is showing, the server isn&apos;t answering at all.</p></div>
      ) : (
        <>
          <p className="admin-sum">
            Server started {ago(h.started)}. These checks refresh with the rest of the page.
          </p>
          <ul className="health">
            {h.checks.map((c) => (
              <li key={c.title} className={"health-item glass health-item--" + c.level}>
                <span className="health-dot" aria-hidden="true" />
                <div>
                  <b>{c.title}</b>
                  <p>{c.detail}</p>
                </div>
                <span className="health-level">{LEVEL_LABEL[c.level]}</span>
              </li>
            ))}
          </ul>

          <h2 className="admin-h">Recent crashes</h2>
          {h.errors.length === 0 ? (
            <div className="gate glass"><p>No request crashed in the last 7 days.</p></div>
          ) : (
            <div className="table-wrap glass">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>When</th>
                    <th>Request</th>
                    <th>What went wrong</th>
                  </tr>
                </thead>
                <tbody>
                  {h.errors.map((e, i) => (
                    <tr key={i}>
                      <td>{when(e.ts)}</td>
                      <td>{e.method} {e.path}</td>
                      <td className="crash-error">{e.error}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="muted">The full details of each crash are in the backend&apos;s terminal (its log).</p>
        </>
      )}

      <h2 className="admin-h">Alerts when nobody is watching</h2>
      <div className="monitor glass">
        <p>
          This page can only warn you while it&apos;s open, and a server that has stopped can&apos;t send a warning itself.
          So once JalSetu is online, sign up for a free uptime monitor (for example UptimeRobot or Better Stack) and give it
          this address:
        </p>
        <code className="monitor-url">{monitorUrl}</code>
        <p>
          It checks every few minutes and texts or emails you when the answer isn&apos;t <code>{'{"ok": true}'}</code>: when the
          website, the backend behind it or the database stops working.
        </p>
      </div>
    </>
  );
}

/** For someone who forgot their password and can't get the SMS: the admin creates a code and reads it to them. */
function PasswordHelp() {
  const [phone, setPhone] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [made, setMade] = useState<ResetCode | null>(null);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      setMade(await api<ResetCode>("/admin/reset-codes", { method: "POST", body: { phone } }));
      setPhone("");
    } catch (e) {
      setMade(null);
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const until = made && new Date(made.expires * 1000).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit" });
  return (
    <>
      <p className="admin-sum">
        A customer or supplier who forgot their password and can&apos;t get the SMS can call JalSetu. First check it&apos;s really
        them, for example by calling them back on the account&apos;s number. Then create a code here and read it to them. They
        enter it under <b>Sign in → Forgot password? → I already have a code</b>.
      </p>
      <form className="reset-help glass" onSubmit={create}>
        <label className="wf-label" htmlFor="rh-phone">Account&apos;s mobile number</label>
        <div className="reset-help-row">
          <input id="rh-phone" className="wf-input" inputMode="tel" placeholder="10-digit mobile" value={phone} onChange={(e) => setPhone(e.target.value)} required />
          <button type="submit" className="pill pill--navy" disabled={busy}>{busy ? "…" : "Create code"}</button>
        </div>
        {err && <p className="form-err" role="alert">{err}</p>}
      </form>
      {made && (
        <div className="reset-code glass" role="status">
          <p>
            Code for <b>{made.name}</b> ({made.role === "user" ? "customer" : made.role}, {made.phone})
          </p>
          <b className="reset-code-digits">{made.code.slice(0, 3)} {made.code.slice(3)}</b>
          <p className="muted">Works once, until {until}. Creating another code for this account cancels this one.</p>
        </div>
      )}
    </>
  );
}

export default function Admin() {
  const { user, toast } = useApp();
  const [tab, setTab] = useState<Tab>("overview");
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [rows, setRows] = useState<AdminSupplier[] | null>(null);
  const [fb, setFb] = useState<Feedback | null>(null);
  const [health, setHealth] = useState<AdminHealth | null>(null);
  const [down, setDown] = useState<number | null>(null); // when the server stopped answering (ms), or null
  const downSince = useRef<number | null>(null);

  const load = useCallback(() => {
    Promise.all([api<AdminOverview>("/admin/overview"), api<AdminSupplier[]>("/admin/suppliers"), api<Feedback>("/admin/feedback")])
      .then(([o, s, f]) => {
        setOverview(o);
        setRows(s);
        setFb(f);
        if (downSince.current) toast("The server is answering again");
        downSince.current = null;
        setDown(null);
      })
      .catch((e) => {
        // no answer, or the website couldn't reach the backend: a red bar that stays, not a pop-up every 30 seconds
        const status = e instanceof ApiError ? e.status : 0;
        if (status === 0 || status >= 500) {
          downSince.current ??= Date.now();
          setDown(downSince.current);
        } else {
          toast(e.message);
        }
      });
    api<AdminHealth>("/admin/health")
      .then(setHealth)
      .catch(() => setHealth(null));
  }, [toast]);

  // live numbers: reload every 30 s while the tab is visible
  useEffect(() => {
    if (user?.role !== "admin") return;
    load();
    const t = setInterval(() => document.visibilityState === "visible" && load(), REFRESH_MS);
    return () => clearInterval(t);
  }, [user, load]);

  async function verify(s: AdminSupplier, v: boolean) {
    try {
      await api(`/admin/suppliers/${s.id}/verify`, { method: "POST", body: { verified: v } });
      toast(v ? `${s.business_name} is now verified` : `${s.business_name} was hidden from customers`);
      load();
    } catch (e) {
      toast((e as Error).message);
    }
  }

  const urgent = health?.checks.filter((c) => c.level === "bad") ?? [];
  const badge: Partial<Record<Tab, number>> = {
    reports: overview?.feedback.reports_open,
    verify: overview?.suppliers.awaiting,
    server: health?.checks.filter((c) => c.level === "bad" || c.level === "warn").length,
  };
  const updated = overview && new Date(overview.generated_at * 1000).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", second: "2-digit" });

  return (
    <PageShell title="Admin dashboard" sub="Orders, suppliers and customer feedback across JalSetu" roles={["admin"]}>
      {down ? (
        <div className="server-alert server-alert--down" role="alert">
          <b>The JalSetu server isn&apos;t answering</b> (since {clock(down)}). Customers probably can&apos;t use the site
          either. Checking again every 30 seconds.
        </div>
      ) : (
        urgent.length > 0 && (
          <div className="server-alert" role="status">
            <b>Server needs attention:</b> {urgent.map((c) => c.title).join(", ")}.
            {tab !== "server" && <button className="link-btn" onClick={() => setTab("server")}>Open Server health</button>}
          </div>
        )
      )}
      <div className="tabs" role="tablist" aria-label="Admin sections">
        {TABS.map(([id, label]) => (
          <button key={id} role="tab" id={"tab-" + id} aria-selected={tab === id} aria-controls="admin-panel" className={tab === id ? "on" : ""} onClick={() => setTab(id)}>
            {label}
            {!!badge[id] && <span className="count">{badge[id]}</span>}
          </button>
        ))}
      </div>
      {updated && (
        <p className="updated">
          Updated {updated} · refreshes every 30 seconds{" "}
          <button className="link-btn" onClick={load}>Refresh now</button>
        </p>
      )}
      <div id="admin-panel" role="tabpanel" aria-labelledby={"tab-" + tab}>
        {tab === "server" ? (
          <ServerHealth h={health} />
        ) : !overview || !rows || !fb ? (
          <p className="muted center">Loading…</p>
        ) : tab === "overview" ? (
          <Overview o={overview} />
        ) : tab === "suppliers" ? (
          <SupplierTable rows={rows} />
        ) : tab === "reports" ? (
          <Reports fb={fb} onChange={load} />
        ) : tab === "help" ? (
          <PasswordHelp />
        ) : (
          <Verification rows={rows} onVerify={verify} onChange={load} />
        )}
      </div>
    </PageShell>
  );
}
