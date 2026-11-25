/** A small line under a heading: a pulsing green dot while auto-refresh works, red when the last refresh failed. */
export default function LiveNote({ stale, children }: { stale: boolean; children: React.ReactNode }) {
  return (
    <p className={"live" + (stale ? " live--stale" : "")} role="status">
      {stale ? "Couldn't refresh just now. Trying again…" : children}
    </p>
  );
}
