import { useEffect, useRef } from "react";
import { DispatchWebSocket } from "../api/websocket";
import { useAuthStore } from "../stores/authStore";
import { useRealtimeStore } from "../stores/realtimeStore";
import type { WebSocketMessage } from "../types";

export function useWebSocket() {
  const token = useAuthStore((s) => s.token);
  const updateDriverLocation = useRealtimeStore((s) => s.updateDriverLocation);
  const wsRef = useRef<DispatchWebSocket | null>(null);

  useEffect(() => {
    if (!token) return;

    const ws = new DispatchWebSocket(token);
    wsRef.current = ws;

    const unsubscribe = ws.onMessage((message: WebSocketMessage) => {
      if (message.type === "driver_location") {
        const msg = message as { driver_id: string; lat: number; lon: number; speed_kmh?: number; heading?: number; timestamp: number };
        updateDriverLocation(msg.driver_id, {
          lat: msg.lat,
          lon: msg.lon,
          speed_kmh: msg.speed_kmh,
          heading: msg.heading,
          timestamp: msg.timestamp,
        });
      }
    });

    ws.connect();

    return () => {
      unsubscribe();
      ws.disconnect();
      wsRef.current = null;
    };
  }, [token, updateDriverLocation]);

  return wsRef;
}
