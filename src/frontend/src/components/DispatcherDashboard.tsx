import React, { useState, useEffect } from "react";
import { useDispatcherWebSocket } from "../hooks/useDispatcherWebSocket";

interface DriverTelemetry {
  driver_id: string;
  lat: number;
  lng: number;
  speed: number;
  heading: number;
  timestamp: string;
}

interface DispatcherDashboardProps {
  authToken: string;
}

export const DispatcherDashboard: React.FC<DispatcherDashboardProps> = ({ authToken }) => {
  const { isConnected, lastMessage } = useDispatcherWebSocket(authToken);
  const [vehicles, setVehicles] = useState<Record<string, DriverTelemetry>>({});
  const [eventsLog, setEventsLog] = useState<string[]>([]);

  useEffect(() => {
    if (!lastMessage) return;

    const { event, data } = lastMessage;
    
    // Log incoming event
    setEventsLog((prev) => [
      `[${new Date().toLocaleTimeString()}] Event: ${event} - Driver: ${data.driver_id || "N/A"}`,
      ...prev.slice(0, 49) // Keep last 50 events
    ]);

    if (event === "location_update" && data.driver_id) {
      setVehicles((prev) => ({
        ...prev,
        [data.driver_id]: data
      }));
    }
  }, [lastMessage]);

  return (
    <div style={{ padding: "24px", fontFamily: "Arial, sans-serif", backgroundColor: "#f4f6f8", minHeight: "100vh" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <h1>Fleet Command & Dispatcher Dashboard</h1>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <span style={{
            height: "12px",
            width: "12px",
            borderRadius: "50%",
            backgroundColor: isConnected ? "#22c55e" : "#ef4444",
            display: "inline-block"
          }} />
          <span style={{ fontWeight: "bold", color: isConnected ? "#166534" : "#991b1b" }}>
            {isConnected ? "Live Connected" : "Disconnected / Reconnecting..."}
          </span>
        </div>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "20px" }}>
        {/* Active Fleet View */}
        <div style={{ background: "white", padding: "20px", borderRadius: "8px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
          <h2>Active Fleet Tracking</h2>
          {Object.keys(vehicles).length === 0 ? (
            <p style={{ color: "#6b7280" }}>Waiting for live telemetry broadcasts from fleet simulator...</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", marginTop: "10px" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
                  <th style={{ padding: "8px" }}>Driver ID</th>
                  <th style={{ padding: "8px" }}>Latitude</th>
                  <th style={{ padding: "8px" }}>Longitude</th>
                  <th style={{ padding: "8px" }}>Speed (mph)</th>
                  <th style={{ padding: "8px" }}>Last Updated</th>
                </tr>
              </thead>
              <tbody>
                {Object.values(vehicles).map((v) => (
                  <tr key={v.driver_id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                    <td style={{ padding: "8px", fontWeight: "bold" }}>{v.driver_id}</td>
                    <td style={{ padding: "8px" }}>{v.lat.toFixed(4)}</td>
                    <td style={{ padding: "8px" }}>{v.lng.toFixed(4)}</td>
                    <td style={{ padding: "8px" }}>{v.speed.toFixed(1)}</td>
                    <td style={{ padding: "8px" }}>{new Date(v.timestamp).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Live Event Stream Sidebar */}
        <div style={{ background: "white", padding: "20px", borderRadius: "8px", boxShadow: "0 1px 3px rgba(0,0,0,0.1)" }}>
          <h2>Live Event Stream</h2>
          <div style={{ background: "#111827", color: "#f9fafb", padding: "12px", borderRadius: "6px", height: "350px", overflowY: "auto", fontSize: "12px", fontFamily: "monospace" }}>
            {eventsLog.length === 0 ? (
              <span style={{ color: "#9ca3af" }}>Listening for events...</span>
            ) : (
              eventsLog.map((log, index) => <div key={index} style={{ marginBottom: "4px" }}>{log}</div>)
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
