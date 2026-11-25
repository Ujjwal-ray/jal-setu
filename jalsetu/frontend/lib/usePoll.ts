import { useEffect, useRef } from "react";

/**
 * Runs `task` every `ms` milliseconds while the page is open, and straight away whenever the tab
 * becomes visible again. A run is skipped if the previous one hasn't finished yet.
 *
 * - `background: false` (the default) skips timer runs while the tab is hidden.
 * - `background: true` keeps checking in a hidden tab. Browsers slow timers there
 *   (Chrome: to about once a minute after the tab has been hidden for 5 minutes), so a check can be late.
 */
export function usePoll(task: () => unknown, ms: number, { enabled = true, background = false } = {}) {
  const latest = useRef(task);
  useEffect(() => {
    latest.current = task;
  });

  useEffect(() => {
    if (!enabled) return;
    let running = false;
    const run = async () => {
      if (running) return;
      running = true;
      try {
        await latest.current();
      } finally {
        running = false;
      }
    };
    const tick = () => {
      if (background || document.visibilityState === "visible") void run();
    };
    const onShow = () => {
      if (document.visibilityState === "visible") void run();
    };
    const timer = setInterval(tick, ms);
    document.addEventListener("visibilitychange", onShow);
    return () => {
      clearInterval(timer);
      document.removeEventListener("visibilitychange", onShow);
    };
  }, [ms, enabled, background]);
}
