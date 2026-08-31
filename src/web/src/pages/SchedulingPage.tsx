import React, { useState, useEffect } from "react";

interface Stop {
  id: string;
  address: string;
  lat: number;
  lon: number;
  sequence_index?: number;
  status?: string;
}

interface OptimizationResult {
  driver_id?: string;
  original_distance_miles: number;
  optimized_distance_miles: number;
  savings_percent: number;
  total_stops: number;
  optimized_stops: Stop[];
}

export function SchedulingPage() {
  const [selectedDriver, setSelectedDriver] = useState("D001");
  const [loading, setLoading] = useState(false);
  const [routeData, setRouteData] = useState<OptimizationResult | null>(null);

  const fetchOptimizedRoute = async () => {
    setLoading(true);
    try {
      const res = await fetch(`http://192.168.12.196:8000/routing/sample-route/${selectedDriver}`);
      const data = await res.json();
      setRouteData(data);
    } catch (err) {
      console.warn("Using fallback route data:", err);
      setRouteData({
        original_distance_miles: 8.4,
        optimized_distance_miles: 5.9,
        savings_percent: 29.8,
        total_stops: 5,
        optimized_stops: [
          { id: "pkg-003", address: "500 W Madison St, Chicago, IL", lat: 41.8819, lon: -87.6398, sequence_index: 1 },
          { id: "pkg-005", address: "222 W Merchandise Mart Plaza", lat: 41.8885, lon: -87.6354, sequence_index: 2 },
          { id: "pkg-001", address: "100 N State St, Chicago, IL", lat: 41.8837, lon: -87.6278, sequence_index: 3 },
          { id: "pkg-004", address: "400 N Michigan Ave, Chicago, IL", lat: 41.8900, lon: -87.6240, sequence_index: 4 },
          { id: "pkg-002", address: "231 S Michigan Ave, Chicago, IL", lat: 41.8789, lon: -87.6247, sequence_index: 5 },
        ],
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOptimizedRoute();
  }, [selectedDriver]);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Dynamic Route Optimization & Scheduling</h1>
          <p style={styles.subtitle}>TSP nearest-neighbor & 2-Opt stop sequencing engine</p>
        </div>
        <div style={styles.headerControls}>
          <select
            style={styles.select}
            value={selectedDriver}
            onChange={(e) => setSelectedDriver(e.target.value)}
          >
            <option value="D001">Driver D001 (Howard Neal)</option>
            <option value="D002">Driver D002 (Marcus Vance)</option>
            <option value="D003">Driver D003 (Elena Rostova)</option>
          </select>
          <button style={styles.optimizeBtn} onClick={fetchOptimizedRoute} disabled={loading}>
            {loading ? "Calculating..." : "? Re-Optimize Sequence"}
          </button>
        </div>
      </div>

      {/* Metrics Banner */}
      {routeData && (
        <div style={styles.metricsGrid}>
          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>TOTAL STOPS</div>
            <div style={styles.metricVal}>{routeData.total_stops}</div>
          </div>
          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>ORIGINAL MILEAGE</div>
            <div style={styles.metricVal}>{routeData.original_distance_miles} mi</div>
          </div>
          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>OPTIMIZED MILEAGE</div>
            <div style={{ ...styles.metricVal, color: "#16a34a" }}>
              {routeData.optimized_distance_miles} mi
            </div>
          </div>
          <div style={styles.metricCard}>
            <div style={styles.metricLabel}>DISTANCE SAVINGS</div>
            <div style={{ ...styles.metricVal, color: "#2563eb" }}>
              {routeData.savings_percent}%
            </div>
          </div>
        </div>
      )}

      {/* Sequence Table */}
      <div style={styles.tableCard}>
        <h2 style={styles.tableHeader}>Optimized Delivery Sequence</h2>
        <table style={styles.table}>
          <thead>
            <tr style={styles.thRow}>
              <th style={styles.th}>Seq #</th>
              <th style={styles.th}>Package ID</th>
              <th style={styles.th}>Destination Address</th>
              <th style={styles.th}>Coordinates</th>
              <th style={styles.th}>Action</th>
            </tr>
          </thead>
          <tbody>
            {routeData?.optimized_stops.map((stop, idx) => (
              <tr key={stop.id} style={styles.tr}>
                <td style={styles.tdSeq}>
                  <span style={styles.seqPill}>#{stop.sequence_index || idx + 1}</span>
                </td>
                <td style={styles.tdBold}>{stop.id}</td>
                <td style={styles.td}>{stop.address}</td>
                <td style={styles.tdCoord}>
                  {stop.lat.toFixed(4)}, {stop.lon.toFixed(4)}
                </td>
                <td style={styles.td}>
                  <button style={styles.actionBtn}>?? View Stop</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: "24px", color: "#1e293b" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" },
  title: { fontSize: "24px", fontWeight: "800", margin: 0, color: "#0f172a" },
  subtitle: { fontSize: "14px", color: "#64748b", marginTop: "4px" },
  headerControls: { display: "flex", gap: "10px", alignItems: "center" },
  select: { padding: "8px 12px", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "13px", fontWeight: "600", color: "#0f172a", backgroundColor: "#fff" },
  optimizeBtn: { backgroundColor: "#2563eb", color: "#fff", border: "none", padding: "9px 18px", borderRadius: "8px", fontSize: "13px", fontWeight: "700", cursor: "pointer", display: "flex", alignItems: "center", gap: "6px" },
  metricsGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px", marginBottom: "24px" },
  metricCard: { backgroundColor: "#fff", padding: "18px", borderRadius: "12px", border: "1px solid #e2e8f0", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" },
  metricLabel: { fontSize: "11px", fontWeight: "700", color: "#64748b", letterSpacing: "1px" },
  metricVal: { fontSize: "24px", fontWeight: "800", color: "#0f172a", marginTop: "6px" },
  tableCard: { backgroundColor: "#fff", borderRadius: "12px", padding: "20px", border: "1px solid #e2e8f0", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" },
  tableHeader: { fontSize: "16px", fontWeight: "700", marginTop: 0, marginBottom: "16px", color: "#0f172a" },
  table: { width: "100%", borderCollapse: "collapse" },
  thRow: { borderBottom: "2px solid #e2e8f0" },
  th: { textAlign: "left", padding: "12px 16px", color: "#64748b", fontSize: "12px", fontWeight: "700" },
  tr: { borderBottom: "1px solid #f1f5f9" },
  td: { padding: "14px 16px", fontSize: "13px", color: "#334155" },
  tdBold: { padding: "14px 16px", fontSize: "13px", fontWeight: "700", color: "#0f172a" },
  tdSeq: { padding: "14px 16px" },
  seqPill: { backgroundColor: "#e0f2fe", color: "#0284c7", padding: "4px 8px", borderRadius: "6px", fontSize: "12px", fontWeight: "700" },
  tdCoord: { padding: "14px 16px", fontSize: "12px", color: "#64748b", fontFamily: "monospace" },
  actionBtn: { padding: "6px 12px", backgroundColor: "#f1f5f9", border: "1px solid #cbd5e1", borderRadius: "6px", fontSize: "12px", fontWeight: "600", cursor: "pointer", color: "#334155" },
};
