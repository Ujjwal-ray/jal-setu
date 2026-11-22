import Link from "next/link";
import { Logo } from "./Icons";

export default function Footer({ plain }: { plain?: boolean }) {
  return (
    <footer className={"footer" + (plain ? " footer--plain" : "")}>
      <div className="footer-inner">
        <Logo />
        <p className="footer-tag">Smart water-jar delivery &amp; supplier locator</p>
        <nav className="footer-nav" aria-label="Footer">
          <Link href="/#suppliers">Find suppliers</Link>
          <Link href="/#order">Request delivery</Link>
          <Link href="/requests">My requests</Link>
          <Link href="/supplier">For suppliers</Link>
          <Link href="/admin">Admin</Link>
        </nav>
        <p className="footer-small">
          A Design Thinking Lab project · Dept. of Information Technology, RCCIIT (Autonomous), Kolkata
          <br />
          Map data © OpenStreetMap contributors · © {new Date().getFullYear()} JalSetu
        </p>
      </div>
    </footer>
  );
}
