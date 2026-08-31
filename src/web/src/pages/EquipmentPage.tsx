import React, { useState, useEffect } from "react";

interface EquipmentItem {
  id: string;
  barcode: string;
  name: string;
  type: string;
  serial_number: string;
  status: "AVAILABLE" | "CHECKED_OUT" | "MAINTENANCE";
  assigned_driver_id: string | null;
  battery_level?: number;
  odometer_miles?: number;
  fuel_percent?: number;
  checked_out_at?: string;
}

export function EquipmentPage() {
  const [equipmentList, setEquipmentList] = useState<EquipmentItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [scanInput, setScanInput] = useState("");
  const [selectedDriver, setSelectedDriver] = useState("D001");
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchEquipment = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://192.168.12.196:8000/equipment/list");
      const data = await res.json();
      setEquipmentList(data);
    } catch (err) {
      console.warn("Using fallback inventory:", err);
      setEquipmentList([
        {
          id: "EQ-SCN-101",
          barcode: "SCN-TC57-101",
          name: "Zebra TC57 Handheld Scanner",
          type: "SCANNER",
          serial_number: "ZB-99381-A",
          status: "CHECKED_OUT",
          assigned_driver_id: "D001",
          battery_level: 94,
        },
        {
          id: "EQ-SCN-102",
          barcode: "SCN-TC57-102",
          name: "Zebra TC57 Handheld Scanner",
          type: "SCANNER",
          serial_number: "ZB-99382-B",
          status: "AVAILABLE",
          assigned_driver_id: null,
          battery_level: 100,
        },
        {
          id: "EQ-VAN-501",
          barcode: "VAN-SPRINTER-501",
          name: "Mercedes Sprinter 2500 (Van #5)",
          type: "VEHICLE",
          serial_number: "VIN-4JGDA5EB8PA102938",
          status: "CHECKED_OUT",
          assigned_driver_id: "D001",
          odometer_miles: 41280,
          fuel_percent: 88,
        },
        {
          id: "EQ-VAN-502",
          barcode: "VAN-SPRINTER-502",
          name: "Ford Transit Cargo 350 (Van #6)",
          type: "VEHICLE",
          serial_number: "VIN-1FTYR2Y84MKA49281",
          status: "AVAILABLE",
          assigned_driver_id: null,
          odometer_miles: 28450,
          fuel_percent: 95,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEquipment();
  }, []);

  const handleEquipmentAction = async (barcodeOrId: string, action: "CHECK_OUT" | "CHECK_IN") => {
    try {
      const res = await fetch("http://192.168.12.196:8000/equipment/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          barcode_or_id: barcodeOrId,
          driver_id: selectedDriver,
          action: action,
          battery_level: action === "CHECK_IN" ? 88 : undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Action failed");

      setActionMessage(`Asset ${barcodeOrId} successfully marked as ${action === "CHECK_OUT" ? "Checked Out to " + selectedDriver : "Returned / Available"}`);
      fetchEquipment();
      setScanInput("");
    } catch (err: any) {
      setActionMessage(`Error: ${err.message}`);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div>
          <h1 style={styles.title}>Depot Equipment & Asset Management</h1>
          <p style={styles.subtitle}>Handheld scanners, delivery vehicles, and mobile terminal check-in/out</p>
        </div>
        <button style={styles.refreshBtn} onClick={fetchEquipment}>
          ?? Refresh Inventory
        </button>
      </div>

      {/* Barcode Quick Action Bar */}
      <div style={styles.scanCard}>
        <div style={styles.scanHeader}>?? Rapid Barcode Scan / Check-In / Check-Out</div>
        <div style={styles.scanForm}>
          <input
            type="text"
            placeholder="Scan asset barcode (e.g. SCN-TC57-102 or EQ-VAN-502)"
            value={scanInput}
            onChange={(e) => setScanInput(e.target.value)}
            style={styles.input}
          />
          <select
            value={selectedDriver}
            onChange={(e) => setSelectedDriver(e.target.value)}
            style={styles.select}
          >
            <option value="D001">Driver D001 (Howard Neal)</option>
            <option value="D002">Driver D002 (Marcus Vance)</option>
            <option value="D003">Driver D003 (Elena Rostova)</option>
          </select>
          <button
            style={styles.checkOutBtn}
            onClick={() => handleEquipmentAction(scanInput, "CHECK_OUT")}
            disabled={!scanInput.trim()}
          >
            ?? Check Out
          </button>
          <button
            style={styles.checkInBtn}
            onClick={() => handleEquipmentAction(scanInput, "CHECK_IN")}
            disabled={!scanInput.trim()}
          >
            ?? Return / Check In
          </button>
        </div>
        {actionMessage && <div style={styles.actionBanner}>{actionMessage}</div>}
      </div>

      {/* Asset Grid */}
      <div style={styles.grid}>
        {equipmentList.map((item) => {
          const isAvailable = item.status === "AVAILABLE";
          return (
            <div key={item.id} style={styles.card}>
              <div style={styles.cardTop}>
                <span style={styles.assetType}>{item.type}</span>
                <span style={isAvailable ? styles.statusAvail : styles.statusOut}>
                  {item.status}
                </span>
              </div>
              <h3 style={styles.assetName}>{item.name}</h3>
              <div style={styles.codeRow}>
                <span style={styles.assetId}>{item.id}</span>
                <span style={styles.barcodeText}>?? {item.barcode}</span>
              </div>

              <div style={styles.detailBox}>
                <div style={styles.metaRow}>
                  <span style={styles.metaLabel}>Assigned Driver:</span>
                  <span style={styles.metaVal}>{item.assigned_driver_id || "Unassigned (Depot)"}</span>
                </div>
                {item.battery_level !== undefined && (
                  <div style={styles.metaRow}>
                    <span style={styles.metaLabel}>Battery Level:</span>
                    <span style={styles.metaVal}>? {item.battery_level}%</span>
                  </div>
                )}
                {item.odometer_miles !== undefined && (
                  <div style={styles.metaRow}>
                    <span style={styles.metaLabel}>Odometer:</span>
                    <span style={styles.metaVal}>?? {item.odometer_miles.toLocaleString()} mi</span>
                  </div>
                )}
              </div>

              <div style={styles.cardActions}>
                {isAvailable ? (
                  <button
                    style={styles.btnActionOut}
                    onClick={() => handleEquipmentAction(item.id, "CHECK_OUT")}
                  >
                    Assign & Check Out
                  </button>
                ) : (
                  <button
                    style={styles.btnActionIn}
                    onClick={() => handleEquipmentAction(item.id, "CHECK_IN")}
                  >
                    Check In to Depot
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { padding: "24px", color: "#1e293b" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" },
  title: { fontSize: "24px", fontWeight: "800", margin: 0, color: "#0f172a" },
  subtitle: { fontSize: "14px", color: "#64748b", marginTop: "4px" },
  refreshBtn: { backgroundColor: "#f1f5f9", border: "1px solid #cbd5e1", padding: "8px 14px", borderRadius: "8px", fontSize: "13px", fontWeight: "600", cursor: "pointer", color: "#334155" },
  scanCard: { backgroundColor: "#fff", padding: "20px", borderRadius: "12px", border: "1px solid #e2e8f0", marginBottom: "24px", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" },
  scanHeader: { fontSize: "14px", fontWeight: "700", color: "#0f172a", marginBottom: "12px" },
  scanForm: { display: "flex", gap: "10px", flexWrap: "wrap" },
  input: { flex: 1, minWidth: "260px", padding: "10px 14px", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "13px" },
  select: { padding: "10px 14px", borderRadius: "8px", border: "1px solid #cbd5e1", fontSize: "13px", backgroundColor: "#fff" },
  checkOutBtn: { backgroundColor: "#2563eb", color: "#fff", border: "none", padding: "10px 18px", borderRadius: "8px", fontWeight: "700", cursor: "pointer" },
  checkInBtn: { backgroundColor: "#16a34a", color: "#fff", border: "none", padding: "10px 18px", borderRadius: "8px", fontWeight: "700", cursor: "pointer" },
  actionBanner: { marginTop: "12px", padding: "10px 14px", backgroundColor: "#f0fdf4", color: "#15803d", borderRadius: "8px", fontSize: "13px", fontWeight: "600" },
  grid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "18px" },
  card: { backgroundColor: "#fff", borderRadius: "12px", border: "1px solid #e2e8f0", padding: "18px", display: "flex", flexDirection: "column", justifyContent: "space-between", boxShadow: "0 1px 3px rgba(0,0,0,0.05)" },
  cardTop: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" },
  assetType: { fontSize: "11px", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.5px" },
  statusAvail: { backgroundColor: "#dcfce7", color: "#15803d", padding: "3px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: "700" },
  statusOut: { backgroundColor: "#fef3c7", color: "#b45309", padding: "3px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: "700" },
  assetName: { fontSize: "16px", fontWeight: "800", color: "#0f172a", margin: "4px 0 10px 0" },
  codeRow: { display: "flex", gap: "10px", alignItems: "center", marginBottom: "14px" },
  assetId: { fontSize: "12px", fontWeight: "700", color: "#2563eb", backgroundColor: "#eff6ff", padding: "2px 8px", borderRadius: "4px" },
  barcodeText: { fontSize: "12px", color: "#64748b", fontFamily: "monospace" },
  detailBox: { backgroundColor: "#f8fafc", padding: "12px", borderRadius: "8px", marginBottom: "16px", display: "flex", flexDirection: "column", gap: "6px" },
  metaRow: { display: "flex", justifyContent: "space-between", fontSize: "12px" },
  metaLabel: { color: "#64748b", fontWeight: "500" },
  metaVal: { color: "#0f172a", fontWeight: "700" },
  cardActions: { marginTop: "auto" },
  btnActionOut: { width: "100%", backgroundColor: "#2563eb", color: "#fff", border: "none", padding: "10px", borderRadius: "8px", fontWeight: "700", cursor: "pointer", fontSize: "13px" },
  btnActionIn: { width: "100%", backgroundColor: "#16a34a", color: "#fff", border: "none", padding: "10px", borderRadius: "8px", fontWeight: "700", cursor: "pointer", fontSize: "13px" },
};
