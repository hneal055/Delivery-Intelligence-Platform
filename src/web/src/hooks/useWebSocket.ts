import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { notifications } from "@mantine/notifications";
import { DispatchWebSocket } from "../api/websocket";
import { useAuthStore } from "../stores/authStore";
import { useRealtimeStore } from "../stores/realtimeStore";
import type { WebSocketMessage } from "../types";

export function useWebSocket() {
  const token = useAuthStore((s) => s.token);
  const updateDriverLocation = useRealtimeStore((s) => s.updateDriverLocation);
  const wsRef = useRef<DispatchWebSocket | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!token) return;

    const ws = new DispatchWebSocket(token);
    wsRef.current = ws;

    const unsubscribe = ws.onMessage((message: WebSocketMessage) => {
      if ((message as { type: string }).type === "problem_reported") {
        const msg = message as unknown as { driver_id: string; reason: string; address: string | null };
        notifications.show({
          color: "red",
          autoClose: false,
          title: `Problem reported by ${msg.driver_id}`,
          message: `${msg.reason}${msg.address ? ` — ${msg.address}` : ""}`,
        });
        queryClient.invalidateQueries({ queryKey: ["packages"] });
        return;
      }
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
  }, [token, updateDriverLocation, queryClient]);

  return wsRef;
}
