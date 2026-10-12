import { useEffect, useRef } from "react";
import { notifications } from "@mantine/notifications";
import { useAttention } from "./useAttention";

/** Short two-tone chime; browsers may block it until the page is clicked once. */
function chime() {
  try {
    const ctx = new AudioContext();
    [880, 660].forEach((freq, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0.15, ctx.currentTime + i * 0.18);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.18 + 0.16);
      osc.connect(gain).connect(ctx.destination);
      osc.start(ctx.currentTime + i * 0.18);
      osc.stop(ctx.currentTime + i * 0.18 + 0.17);
    });
    setTimeout(() => ctx.close(), 600);
  } catch {
    // No audio available: the pop-up still shows.
  }
}

/**
 * On any page: pop up and chime when a new urgent (red) item appears.
 * Items already there when the dashboard opens are shown in the panel,
 * not announced again.
 */
export function useAttentionAlerts() {
  const { data: items } = useAttention();
  const known = useRef<Set<string> | null>(null);

  useEffect(() => {
    if (!items) return;
    const red = items.filter((i) => i.severity === "red");
    if (known.current === null) {
      known.current = new Set(red.map((i) => i.key));
      return;
    }
    const fresh = red.filter((i) => !known.current!.has(i.key));
    known.current = new Set(red.map((i) => i.key));
    if (fresh.length === 0) return;
    for (const item of fresh) {
      notifications.show({ color: "red", autoClose: 15000, title: item.title, message: item.detail });
    }
    chime();
  }, [items]);

  return items ?? [];
}
