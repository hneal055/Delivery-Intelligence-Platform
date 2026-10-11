import { useEffect, useRef } from "react";
import { AppState } from "react-native";
import { getMyPackages } from "../api/client";
import { showLocalAlert } from "../services/notificationService";

const POLL_MS = 30000;

/**
 * While the app is open, check the driver's packages every 30 s and alert
 * on new assignments and pickups that just became ready. The first check
 * only records what is already there, so logging in does not replay
 * old work as "new". Each check also keeps the driver shown as Online.
 */
export function useAssignmentWatcher(enabled) {
  const known = useRef(null); // id -> ready_at

  useEffect(() => {
    if (!enabled) {
      known.current = null;
      return undefined;
    }

    let stopped = false;

    async function check() {
      if (AppState.currentState !== "active") return;
      let packages;
      try {
        packages = await getMyPackages();
      } catch {
        return; // offline: try again next round
      }
      if (stopped) return;

      const open = packages.filter((p) => p.status !== "delivered" && p.status !== "exception");
      const previous = known.current;
      known.current = new Map(open.map((p) => [p.id, p.ready_at]));
      if (previous === null) return;

      for (const p of open) {
        if (!previous.has(p.id)) {
          const where = p.pickup_address ? `Pick up at ${p.pickup_address}` : p.dest_address;
          await showLocalAlert(
            "assigned",
            p.id,
            p.pickup_address ? "New pickup & delivery" : "New delivery",
            where || p.id
          );
        } else if (p.pickup_address && p.ready_at && !previous.get(p.id)) {
          await showLocalAlert("ready", p.id, "Ready for pickup", p.pickup_address);
        }
      }
    }

    check();
    const timer = setInterval(check, POLL_MS);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [enabled]);
}
