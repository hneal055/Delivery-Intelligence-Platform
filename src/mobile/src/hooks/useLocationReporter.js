import { useEffect } from "react";
import { AppState } from "react-native";
import * as Location from "expo-location";
import { reportLocation } from "../api/client";

const REPORT_MS = 30000;

/**
 * While the app is open and the driver is logged in, send the phone's
 * position every 30 s so dispatch sees the driver on the map. Uses the real
 * GPS only (never the dev "Chicago Sim" location). Without location
 * permission, or offline, it quietly skips that round; the map greys the
 * dot out once the position is old.
 */
export function useLocationReporter(driverId) {
  useEffect(() => {
    if (!driverId) return undefined;

    let stopped = false;
    let busy = false;

    async function report() {
      if (busy || AppState.currentState !== "active") return;
      busy = true;
      try {
        let { status } = await Location.getForegroundPermissionsAsync();
        if (status !== "granted") {
          ({ status } = await Location.requestForegroundPermissionsAsync());
        }
        if (status !== "granted" || stopped) return;

        const { coords } = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });
        if (stopped) return;
        await reportLocation(driverId, coords);
      } catch {
        // No fix or no connection: try again next round.
      } finally {
        busy = false;
      }
    }

    report();
    const timer = setInterval(report, REPORT_MS);
    // Report straight away when the driver comes back to the app.
    const sub = AppState.addEventListener("change", (state) => {
      if (state === "active") report();
    });
    return () => {
      stopped = true;
      clearInterval(timer);
      sub.remove();
    };
  }, [driverId]);
}
