import React, { useState, useEffect } from "react";

interface FleetSummary {
  report_date?: string;
  total_active_drivers: number;
  total_manifest_packages: number;
  completed_deliveries: number;
  failed_attempts: number;
  fadr_rate_percent: number;
  avg_dwell_minutes: number;
  fleet_avg_speed_mph: number;
}

interface DriverRow {
  id: string;
  name: string;
  assigned: number;
  delivered: number;
  exceptions: number;
  avgDwell: string;
  status: string;
}

const DRIVER_DATA: DriverRow[] = [
  { id: "D001", name: "Howard Neal", assigned: 28, delivered: 24, exceptions: 1, avgDwell: "2.6 min", status: "ONLINE" },
  { id: "D002", name: "Marcus Vance", assigned: 32, delivered: 29, exceptions: 2, avgDwell: "3.1 min", status: "ONLINE" },
  { id: "D003", name: "Elena Rostova", assigned: 24, delivered: 20, exceptions: 0, avgDwell: "2.4 min", status: "ONLINE" },
];

export default function AnalyticsPage() {
  const [summary, setSummary] = useState<FleetSummary>({
    total_active_drivers: 6,
    total_manifest_packages: 148,
    completed_deliveries: 112,
    failed_attempts: 5,
    fadr_rate_percent: 95.7,
    avg_dwell_minutes: 2.8,
    fleet_avg_speed_mph: 18.4,
  });

  useEffect(() => {
    fetch("http://192.168.12.196:8000/analytics/summary")
      .then((r) => r.json())
      .then((data) => setSummary(data))
      .catch((err) => console.warn("Analytics fetch fallback:", err));
  }, []);

  const completionRate = (
    (summary.completed_deliveries / (summary.total_manifest_packages || 1)) *
    100
  ).toFixed(1);

  // CSV Export Handler
  const exportToCSV = () => {
    const reportDate = new Date().toISOString().split("T")[0];
    const headers = ["Driver ID", "Driver Name", "Assigned Packages", "Delivered", "Exceptions", "Completion Rate (%)", "Avg Dwell Time", "Status", "Report Date"];
    
    const rows = DRIVER_DATA.map((driver) => {
      const rate = ((driver.delivered / (driver.assigned || 1)) * 100).toFixed(1);
      return [
        driver.id,
        `"${driver.name}"`,
        driver.assigned,
        driver.delivered,
        driver.exceptions,
        `${rate}%`,
        `"${driver.avgDwell}"`,
        driver.status,
        reportDate,
      ].join(",");
    });

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `fleet_performance_report_${reportDate}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Fleet Performance & Analytics</h1>
          <p style={styles.subtitle}>Real-time telemetry and driver KPI scorecard</p>
        </div>
        <div style={styles.headerActions}>
          <span style={styles.dateBadge}>Today • Chicago Fleet</span>
          <button style={styles.exportBtn} onClick={exportToCSV}>
            ?? Export CSV
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={styles.grid}>
        <div style={styles.card}>
          <div style={styles.cardTitle}>COMPLETION RATE</div>
          <div style={styles.cardValue}>{completionRate}%</div>
          <div style={styles.cardSub}>
            {summary.completed_deliveries} of {summary.total_manifest_packages} delivered
          </div>
        </div>

        <div style={styles.card}>
          <div style={styles.cardTitle}>AVG DWELL TIME</div>
          <div style={styles.cardValue}>{summary.avg_dwell_minutes} min</div>
          <div style={styles.cardSub}>Target: &lt; 3.5 min/stop</div>
        </div>

        <div style={styles.card}>
          <div style={styles.cardTitle}>FIRST-ATTEMPT SUCCESS</div>
          <div style={styles.cardValue}>{summary.fadr_rate_percent}%</div>
          <div style={styles.cardSub}>Target: &ge; 95.0%</div>
        </div>

        <div style={styles.card}>
          <div style={styles.cardTitle}>ACTIVE DRIVERS</div>
          <div style={styles.cardValue}>{summary.total_active_drivers}</div>
          <div style={styles.cardSub}>Fleet Avg Speed: {summary.fleet_avg_speed_mph} mph</div>
        </div>
      </div>

      {/* Driver Performance Leaderboard */}
      <div style={styles.tableCard}>
        <div style={styles.tableHeaderRow}>
          <h2 style={styles.tableHeader}>Driver Performance Leaderboard</h2>
          <span style={styles.tableSub}>Click Export CSV to download the complete shift record</span>
        </div>
        <table style={styles.table}>
          <thead>
            <tr style={styles.thRow}>
              <th style={styles.th}>Driver</th>
              <th style={styles.th}>Assigned</th>
              <th style={styles.th}>Delivered</th>
              <th style={styles.th}>Exceptions</th>
              <th style={styles.th}>Avg Dwell</th>
              <th style={styles.th}>Status</th>
            </tr>
          </thead>
          <tbody>
            {DRIVER_DATA.map((driver) => (
              <tr key={driver.id} style={styles.tr}>
                <td style={styles.tdBold}>{driver.id} ({driver.name})</td>
                <td style={styles.td}>{driver.assigned}</td>
                <td style={styles.td}>{driver.delivered}</td>
                <td style={styles.td}>{driver.exceptions}</td>
                <td style={styles.td}>{driver.avgDwell}</td>
                <td style={styles.td}>
                  <span style={styles.onlineBadge}>{driver.status}</span>
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
  headerActions: { display: "flex", alignItems: "center", gap: "12px" },
  title: { fontSize: "24px", fontWeight: "800", margin: 0, color: "#0f172a" },
  subtitle: { fontSize: "14px", color: "#64748b", marginTop: "4px" },
  dateBadge: { backgroundColor: "#e0f2fe", padding: "8px 14px", borderRadius: "8px", fontSize: "13px", color: "#0284c7", fontWeight: "700" },
  exportBtn: { backgroundColor: "#2563eb", color: "#ffffff", border: "none", padding: "8px 16px", borderRadius: "8px", fontSize: "13px", fontWeight: "700", cursor: "pointer", display: "flex", alignItems: "center", gap: "6px", boxShadow: "0 1px 2px rgba(0,0,0,0.05)" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px", marginBottom: "28px" },
  card: { backgroundColor: "#fff", padding: "20px", borderRadius: "12px", border: "1px solid #e2e8f0", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" },
  cardTitle: { fontSize: "11px", fontWeight: "700", color: "#64748b", letterSpacing: "1px" },
  cardValue: { fontSize: "28px", fontWeight: "800", color: "#2563eb", margin: "10px 0" },
  cardSub: { fontSize: "12px", color: "#94a3b8" },
  tableCard: { backgroundColor: "#fff", borderRadius: "12px", padding: "20px", border: "1px solid #e2e8f0", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" },
  tableHeaderRow: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" },
  tableHeader: { fontSize: "16px", fontWeight: "700", margin: 0, color: "#0f172a" },
  tableSub: { fontSize: "12px", color: "#64748b" },
  table: { width: "100%", borderCollapse: "collapse" },
  thRow: { borderBottom: "2px solid #e2e8f0" },
  th: { textAlign: "left", padding: "12px 16px", color: "#64748b", fontSize: "12px", fontWeight: "700" },
  tr: { borderBottom: "1px solid #f1f5f9" },
  td: { padding: "14px 16px", fontSize: "13px", color: "#334155" },
  tdBold: { padding: "14px 16px", fontSize: "13px", fontWeight: "700", color: "#0f172a" },
  onlineBadge: { backgroundColor: "#dcfce7", color: "#15803d", padding: "4px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: "700" },
};
