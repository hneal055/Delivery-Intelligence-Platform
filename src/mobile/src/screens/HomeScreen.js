import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  Modal,
  StyleSheet,
  ActivityIndicator,
  Alert,
  Platform,
  RefreshControl,
  SafeAreaView,
} from "react-native";
import { useFocusEffect } from "@react-navigation/native";
import client from "../api/client";
import { useAuthStore } from "../stores/authStore";
import SignaturePad from "../components/SignaturePad";
import { registerForPushNotificationsAsync } from "../services/notificationService";
import {
  initOfflineDatabase,
  queueDeliveryConfirmation,
  processOfflineQueue,
  getPendingQueueCount,
} from "../services/offlineQueueService";

const ROUTE_WAYPOINTS = [
  { lat: 41.8786, lon: -87.6403, label: "Union Station Depot" },
  { lat: 41.8789, lon: -87.6359, label: "Willis Tower Loop" },
  { lat: 41.8826, lon: -87.6226, label: "Millennium Park Stop" },
  { lat: 41.8917, lon: -87.6278, label: "River North Hub" },
  { lat: 41.8885, lon: -87.6354, label: "Merchandise Mart" },
  { lat: 41.8819, lon: -87.6375, label: "Financial District" },
];

const INITIAL_PACKAGES = [
  { id: "pkg-001", address: "100 N State St, Chicago, IL", status: "OUT_FOR_DELIVERY" },
  { id: "pkg-002", address: "231 S Michigan Ave, Chicago, IL", status: "OUT_FOR_DELIVERY" },
  { id: "pkg-003", address: "500 W Madison St, Chicago, IL", status: "OUT_FOR_DELIVERY" },
];

export default function HomeScreen({ navigation, route }) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const [deliveries, setDeliveries] = useState(INITIAL_PACKAGES);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedPkg, setSelectedPkg] = useState(null);
  const [detailsModalVisible, setDetailsModalVisible] = useState(false);
  const [signatureModalVisible, setSignatureModalVisible] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [isOnline, setIsOnline] = useState(false);
  const [pendingQueueCount, setPendingQueueCount] = useState(0);

  // Simulation state
  const [simActive, setSimActive] = useState(false);
  const [currentWaypointIdx, setCurrentWaypointIdx] = useState(0);
  const waypointRef = useRef(0);

  const getDriverId = () => {
    if (typeof user === "string") {
      const match = user.match(/\d+/);
      return match ? `D${match[0].padStart(3, "0")}` : user;
    }
    if (user?.driver_id) return user.driver_id;
    if (user?.username) {
      const match = user.username.match(/\d+/);
      return match ? `D${match[0].padStart(3, "0")}` : user.username;
    }
    return "D001";
  };

  const driverId = getDriverId();

  // Initialize SQLite & Push Notifications
  useEffect(() => {
    initOfflineDatabase();
    if (driverId) {
      registerForPushNotificationsAsync(driverId);
    }
  }, [driverId]);

  // Transmit location telemetry
  const sendTelemetry = useCallback(
    async (targetLat, targetLon, speed = 18.5) => {
      try {
        const jitter = (Math.random() - 0.5) * 0.0004;
        await client.post(`/tracking/${driverId}/location`, {
          lat: targetLat + jitter,
          lon: targetLon + jitter,
          speed: speed,
          heading: 85.0,
          battery_level: 92,
          timestamp: new Date().toISOString(),
        });
        setIsOnline(true);
      } catch (err) {
        setIsOnline(false);
      }
    },
    [driverId]
  );

  // Routine sync and offline queue drain loop
  const syncQueueAndStatus = useCallback(async () => {
    try {
      const result = await processOfflineQueue();
      if (result?.syncedCount > 0) {
        console.log(`[Sync] Flushed ${result.syncedCount} queued deliveries.`);
      }
    } catch (err) {
      console.warn("[Sync] Error draining offline queue:", err);
    } finally {
      const count = await getPendingQueueCount();
      setPendingQueueCount(count);
    }
  }, []);

  // Screen focus hook: re-evaluates queue counts every time driver returns to Manifest
  useFocusEffect(
    useCallback(() => {
      syncQueueAndStatus();
    }, [syncQueueAndStatus])
  );

  // Catch package delivery events passed back from ScannerScreen
  useEffect(() => {
    if (route.params?.deliveredPackageId) {
      const pkgId = route.params.deliveredPackageId;
      setDeliveries((prev) =>
        prev.map((item) =>
          (item.id || item.tracking_number) === pkgId
            ? { ...item, status: "DELIVERED" }
            : item
        )
      );
      syncQueueAndStatus();
      // Clear parameter to avoid re-triggering on subsequent renders
      navigation.setParams({ deliveredPackageId: null });
    }
  }, [route.params?.deliveredPackageId, syncQueueAndStatus, navigation]);

  // Regular periodic sync loop (every 10s)
  useEffect(() => {
    syncQueueAndStatus();
    const timer = setInterval(syncQueueAndStatus, 10000);
    return () => clearInterval(timer);
  }, [syncQueueAndStatus]);

  // Heartbeat when idle
  useEffect(() => {
    if (simActive) return;
    const currentPoint = ROUTE_WAYPOINTS[waypointRef.current];
    sendTelemetry(currentPoint.lat, currentPoint.lon, 0.0);

    const timer = setInterval(() => {
      const pt = ROUTE_WAYPOINTS[waypointRef.current];
      sendTelemetry(pt.lat, pt.lon, 0.0);
    }, 10000);

    return () => clearInterval(timer);
  }, [simActive, sendTelemetry]);

  // Simulation loop
  useEffect(() => {
    if (!simActive) return;

    const interval = setInterval(() => {
      const nextIdx = (waypointRef.current + 1) % ROUTE_WAYPOINTS.length;
      waypointRef.current = nextIdx;
      setCurrentWaypointIdx(nextIdx);

      const target = ROUTE_WAYPOINTS[nextIdx];
      sendTelemetry(target.lat, target.lon, 24.5);
    }, 3500);

    return () => clearInterval(interval);
  }, [simActive, sendTelemetry]);

  const toggleSimulation = () => {
    setSimActive((prev) => !prev);
  };

  const fetchDeliveries = useCallback(async () => {
    try {
      const res = await client.get("/delivery/recent-proofs");
      if (res.data && Array.isArray(res.data) && res.data.length > 0) {
        console.log("Proofs sync:", res.data.length);
      }
    } catch (err) {
      console.warn("Proof sync error:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchDeliveries();
  }, [fetchDeliveries]);

  const onRefresh = async () => {
    setRefreshing(true);
    await syncQueueAndStatus();
    fetchDeliveries();
    const pt = ROUTE_WAYPOINTS[waypointRef.current];
    sendTelemetry(pt.lat, pt.lon, simActive ? 22.0 : 0.0);
  };

  const handleCardPress = (pkg) => {
    setSelectedPkg(pkg);
    setDetailsModalVisible(true);
  };

  const openSignatureCapture = () => {
    setDetailsModalVisible(false);
    setSignatureModalVisible(true);
  };

  const handleConfirmDeliveryWithSignature = async (signatureData) => {
    if (!selectedPkg) return;
    setActionLoading(true);
    const pkgId = selectedPkg.id || selectedPkg.tracking_number;
    const curPoint = ROUTE_WAYPOINTS[waypointRef.current];

    try {
      const formData = new FormData();
      formData.append("package_id", pkgId);
      formData.append("driver_id", driverId);
      formData.append("dest_lat", String(curPoint.lat));
      formData.append("dest_lon", String(curPoint.lon));
      formData.append("signature_path", signatureData || "");

      if (Platform.OS === "web") {
        const byteChars = atob(
          "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        );
        const byteNumbers = new Array(byteChars.length);
        for (let i = 0; i < byteChars.length; i++) {
          byteNumbers[i] = byteChars.charCodeAt(i);
        }
        const blob = new Blob([new Uint8Array(byteNumbers)], { type: "image/png" });
        formData.append("photo", blob, `${pkgId}_signature_proof.png`);
      } else {
        formData.append("photo", {
          uri: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
          name: `${pkgId}_signature_proof.png`,
          type: "image/png",
        });
      }

      await client.post("/delivery/confirm", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setDeliveries((prev) =>
        prev.map((item) =>
          (item.id || item.tracking_number) === pkgId
            ? { ...item, status: "DELIVERED" }
            : item
        )
      );

      const msg = `Package ${pkgId} confirmed & delivered!`;
      if (Platform.OS === "web") window.alert(msg);
      else Alert.alert("Success", msg);

      setSignatureModalVisible(false);
    } catch (err) {
      console.warn("Network failed - enqueueing delivery confirmation offline:", err);

      await queueDeliveryConfirmation({
        packageId: pkgId,
        driverId: driverId,
        lat: curPoint.lat,
        lon: curPoint.lon,
        signaturePath: signatureData,
      });

      setDeliveries((prev) =>
        prev.map((item) =>
          (item.id || item.tracking_number) === pkgId
            ? { ...item, status: "DELIVERED" }
            : item
        )
      );

      const count = await getPendingQueueCount();
      setPendingQueueCount(count);

      const offlineMsg = `Offline Mode: Delivery for ${pkgId} saved locally to SQLite queue. Will sync automatically when connected.`;
      if (Platform.OS === "web") window.alert(offlineMsg);
      else Alert.alert("Saved Offline", offlineMsg);

      setSignatureModalVisible(false);
    } finally {
      setActionLoading(false);
    }
  };

  const renderItem = ({ item }) => {
    const isDelivered = item.status === "DELIVERED";
    const isAttempted = item.status === "ATTEMPTED";

    return (
      <TouchableOpacity
        style={s.card}
        activeOpacity={0.7}
        onPress={() => handleCardPress(item)}
      >
        <View style={s.cardLeft}>
          <Text style={s.pkgId}>{item.id || item.tracking_number}</Text>
          <Text style={s.address}>
            {item.address || item.destination_address || "No address provided"}
          </Text>
        </View>
        <View
          style={[
            s.badge,
            isDelivered
              ? s.badgeDelivered
              : isAttempted
              ? s.badgeAttempted
              : s.badgeOut,
          ]}
        >
          <Text style={s.badgeText}>{item.status || "OUT_FOR_DELIVERY"}</Text>
        </View>
      </TouchableOpacity>
    );
  };

  return (
    <SafeAreaView style={s.safeArea}>
      <View style={s.container}>
        {/* Header */}
        <View style={s.header}>
          <View>
            <Text style={s.heading}>My Deliveries</Text>
            <View style={s.driverRow}>
              <Text style={s.subheading}>{driverId}</Text>
              <View style={[s.statusDot, isOnline ? s.statusOnline : s.statusOffline]} />
              <Text style={s.statusText}>{isOnline ? "ONLINE" : "OFFLINE"}</Text>
              {pendingQueueCount > 0 && (
                <View style={s.queuePill}>
                  <Text style={s.queuePillText}>✓ {pendingQueueCount} queued</Text>
                </View>
              )}
            </View>
            <TouchableOpacity onPress={logout} style={s.signoutBtn}>
              <Text style={s.signout}>Sign out</Text>
            </TouchableOpacity>
          </View>

          <View style={s.headerActions}>
            <TouchableOpacity style={s.refreshHeaderBtn} onPress={onRefresh}>
              <Text style={s.refreshHeaderText}>⟳ Sync</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Live Simulation Banner */}
        <View style={s.simBanner}>
          <View style={s.simInfo}>
            <Text style={s.simTitle}>
              {simActive ? "● ROUTE IN PROGRESS" : "○ GPS IDLE"}
            </Text>
            <Text style={s.simSubtitle}>
              Current: {ROUTE_WAYPOINTS[currentWaypointIdx].label}
            </Text>
          </View>
          <TouchableOpacity
            style={[s.simBtn, simActive ? s.simBtnActive : s.simBtnIdle]}
            onPress={toggleSimulation}
          >
            <Text style={s.simBtnText}>
              {simActive ? "Pause Sim" : "Start Sim"}
            </Text>
          </TouchableOpacity>
        </View>

        {/* Manifest List */}
        {loading ? (
          <ActivityIndicator size="large" color="#2563eb" style={{ marginTop: 40 }} />
        ) : (
          <FlatList
            data={deliveries}
            keyExtractor={(item, index) => item.id || item.tracking_number || String(index)}
            renderItem={renderItem}
            contentContainerStyle={s.listContent}
            refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
            ListEmptyComponent={
              <Text style={s.empty}>No packages assigned for this driver.</Text>
            }
          />
        )}

        {/* Bottom Toolbar */}
        <View style={s.bottomBar}>
          <TouchableOpacity style={s.tabItem} onPress={onRefresh}>
            <Text style={[s.tabLabel, s.tabLabelActive]}>Manifest</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={s.tabScanCenter}
            onPress={() => (navigation?.navigate ? navigation.navigate("Scanner") : null)}
          >
            <Text style={s.scanCenterLabel}>Scan</Text>
          </TouchableOpacity>

          <TouchableOpacity style={s.tabItem} onPress={toggleSimulation}>
            <Text style={s.tabLabel}>{simActive ? "Pause" : "Simulate"}</Text>
          </TouchableOpacity>
        </View>

        {/* Details Modal */}
        <Modal visible={detailsModalVisible} transparent animationType="fade">
          <View style={s.modalBackdrop}>
            <View style={s.modalCard}>
              <Text style={s.modalHeader}>Delivery Details</Text>
              <View style={s.detailRow}>
                <Text style={s.detailLabel}>Tracking ID:</Text>
                <Text style={s.detailVal}>{selectedPkg?.id || selectedPkg?.tracking_number}</Text>
              </View>
              <View style={s.detailRow}>
                <Text style={s.detailLabel}>Address:</Text>
                <Text style={s.detailVal}>
                  {selectedPkg?.address || selectedPkg?.destination_address || "None"}
                </Text>
              </View>
              <View style={s.modalActions}>
                <TouchableOpacity
                  style={[s.modalBtn, s.btnSuccess]}
                  disabled={actionLoading}
                  onPress={openSignatureCapture}
                >
                  <Text style={s.btnTextWhite}>Collect Signature & Deliver</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={[s.modalBtn, s.btnCancel]}
                  onPress={() => setDetailsModalVisible(false)}
                >
                  <Text style={s.btnTextDark}>Cancel</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        </Modal>

        {/* Signature Capture Modal */}
        <Modal visible={signatureModalVisible} transparent animationType="slide">
          <View style={s.modalBackdrop}>
            <SignaturePad
              onConfirm={handleConfirmDeliveryWithSignature}
              onCancel={() => {
                setSignatureModalVisible(false);
                setDetailsModalVisible(true);
              }}
            />
          </View>
        </Modal>
      </View>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#1e293b" },
  container: { flex: 1, backgroundColor: "#f8f9fa" },
  header: {
    backgroundColor: "#1e293b",
    paddingTop: 16,
    paddingBottom: 16,
    paddingHorizontal: 20,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottomWidth: 1,
    borderBottomColor: "#334155",
  },
  heading: { fontSize: 22, fontWeight: "800", color: "#fff" },
  driverRow: { flexDirection: "row", alignItems: "center", marginTop: 4, gap: 6 },
  subheading: { fontSize: 13, color: "#94a3b8", fontWeight: "700" },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  statusOnline: { backgroundColor: "#22c55e" },
  statusOffline: { backgroundColor: "#ef4444" },
  statusText: { fontSize: 11, color: "#cbd5e1", fontWeight: "600" },
  queuePill: {
    backgroundColor: "#d97706",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    marginLeft: 4,
  },
  queuePillText: { color: "#fff", fontSize: 11, fontWeight: "700" },
  signoutBtn: { marginTop: 4 },
  signout: { fontSize: 12, color: "#f87171", textDecorationLine: "underline" },
  headerActions: { flexDirection: "row", alignItems: "center", gap: 8 },
  refreshHeaderBtn: {
    backgroundColor: "#334155",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  refreshHeaderText: { color: "#38bdf8", fontWeight: "700", fontSize: 12 },
  simBanner: {
    backgroundColor: "#0f172a",
    marginHorizontal: 16,
    marginTop: 14,
    marginBottom: 4,
    borderRadius: 12,
    padding: 14,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#334155",
  },
  simInfo: { flex: 1, paddingRight: 10 },
  simTitle: { color: "#38bdf8", fontWeight: "800", fontSize: 13, letterSpacing: 0.5 },
  simSubtitle: { color: "#94a3b8", fontSize: 12, marginTop: 2 },
  simBtn: {
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 8,
  },
  simBtnIdle: { backgroundColor: "#2563eb" },
  simBtnActive: { backgroundColor: "#ea580c" },
  simBtnText: { color: "#fff", fontWeight: "700", fontSize: 12 },
  listContent: { padding: 16, paddingBottom: 90 },
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#e2e8f0",
  },
  cardLeft: { flex: 1, paddingRight: 12 },
  pkgId: { fontSize: 15, fontWeight: "700", color: "#0f172a", marginBottom: 3 },
  address: { fontSize: 13, color: "#64748b" },
  badge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 12 },
  badgeOut: { backgroundColor: "#2563eb" },
  badgeDelivered: { backgroundColor: "#16a34a" },
  badgeAttempted: { backgroundColor: "#dc2626" },
  badgeText: { color: "#fff", fontSize: 11, fontWeight: "700" },
  empty: { textAlign: "center", color: "#94a3b8", marginTop: 40 },
  bottomBar: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    height: 70,
    backgroundColor: "#1e293b",
    borderTopWidth: 1,
    borderTopColor: "#334155",
    flexDirection: "row",
    justifyContent: "space-around",
    alignItems: "center",
    paddingBottom: Platform.OS === "ios" ? 14 : 4,
  },
  tabItem: { alignItems: "center", justifyContent: "center", flex: 1 },
  tabLabel: { color: "#94a3b8", fontSize: 12, fontWeight: "600" },
  tabLabelActive: { color: "#38bdf8" },
  tabScanCenter: {
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#2563eb",
    width: 56,
    height: 56,
    borderRadius: 28,
    marginTop: -20,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 6,
  },
  scanCenterLabel: { color: "#fff", fontSize: 12, fontWeight: "700" },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.6)",
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  modalCard: {
    width: "100%",
    maxWidth: 440,
    backgroundColor: "#fff",
    borderRadius: 16,
    padding: 24,
    elevation: 5,
  },
  modalHeader: { fontSize: 20, fontWeight: "800", marginBottom: 18, color: "#0f172a" },
  detailRow: { marginBottom: 10 },
  detailLabel: { fontSize: 12, color: "#64748b", fontWeight: "600", textTransform: "uppercase" },
  detailVal: { fontSize: 15, color: "#0f172a", fontWeight: "600", marginTop: 2 },
  modalActions: { marginTop: 24, gap: 10 },
  modalBtn: { paddingVertical: 14, borderRadius: 10, alignItems: "center" },
  btnSuccess: { backgroundColor: "#16a34a" },
  btnCancel: { backgroundColor: "#e2e8f0" },
  btnTextWhite: { color: "#fff", fontWeight: "700", fontSize: 14 },
  btnTextDark: { color: "#334155", fontWeight: "700", fontSize: 14 },
});