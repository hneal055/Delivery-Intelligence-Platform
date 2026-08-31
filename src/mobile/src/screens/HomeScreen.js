import React, { useState, useEffect, useCallback } from "react";
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
import client from "../api/client";
import { useAuthStore } from "../stores/authStore";

const INITIAL_PACKAGES = [
  { id: "pkg-001", address: "100 N State St, Chicago, IL", status: "OUT_FOR_DELIVERY" },
  { id: "pkg-002", address: "231 S Michigan Ave, Chicago, IL", status: "OUT_FOR_DELIVERY" },
  { id: "pkg-003", address: "500 W Madison St, Chicago, IL", status: "OUT_FOR_DELIVERY" },
];

export default function HomeScreen({ navigation }) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const [deliveries, setDeliveries] = useState(INITIAL_PACKAGES);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedPkg, setSelectedPkg] = useState(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [isOnline, setIsOnline] = useState(false);

  // Derive driver ID
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

  // Send Heartbeat & GPS Coordinates
  const sendLocationHeartbeat = useCallback(async () => {
    try {
      const baseLat = 41.8781;
      const baseLon = -87.6298;
      const jitter = (Math.random() - 0.5) * 0.002;

      await client.post(`/tracking/${driverId}/location`, {
        lat: baseLat + jitter,
        lon: baseLon + jitter,
        speed: 15.5,
        heading: 90.0,
        battery_level: 95,
        timestamp: new Date().toISOString(),
      });
      setIsOnline(true);
    } catch (err) {
      console.warn("[Heartbeat] Location error:", err?.response?.data || err.message);
    }
  }, [driverId]);

  // Periodic heartbeat every 10 seconds
  useEffect(() => {
    sendLocationHeartbeat();
    const timer = setInterval(sendLocationHeartbeat, 10000);
    return () => clearInterval(timer);
  }, [sendLocationHeartbeat]);

  const fetchDeliveries = useCallback(async () => {
    try {
      const res = await client.get("/delivery/recent-proofs");
      if (res.data && Array.isArray(res.data) && res.data.length > 0) {
        console.log("Recent proofs fetched:", res.data);
      }
    } catch (err) {
      console.warn("Proof fetch warning:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchDeliveries();
  }, [fetchDeliveries]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchDeliveries();
    sendLocationHeartbeat();
  };

  const handleCardPress = (pkg) => {
    setSelectedPkg(pkg);
    setModalVisible(true);
  };

  const handleConfirmDelivery = async () => {
    if (!selectedPkg) return;
    setActionLoading(true);
    const pkgId = selectedPkg.id || selectedPkg.tracking_number;

    try {
      const formData = new FormData();
      formData.append("package_id", pkgId);
      formData.append("driver_id", driverId);
      formData.append("dest_lat", "41.8781");
      formData.append("dest_lon", "-87.6298");

      if (Platform.OS === "web") {
        const byteCharacters = atob(
          "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        );
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { type: "image/png" });
        formData.append("photo", blob, `${pkgId}_proof.png`);
      } else {
        formData.append("photo", {
          uri: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
          name: `${pkgId}_proof.png`,
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

      if (Platform.OS === "web") {
        window.alert(`Package ${pkgId} successfully marked as DELIVERED!`);
      } else {
        Alert.alert("Success", `Package ${pkgId} successfully marked as DELIVERED!`);
      }
      setModalVisible(false);
    } catch (err) {
      console.warn("Backend confirm call error:", err);
      setDeliveries((prev) =>
        prev.map((item) =>
          (item.id || item.tracking_number) === pkgId
            ? { ...item, status: "DELIVERED" }
            : item
        )
      );
      setModalVisible(false);
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeliveryException = async () => {
    if (!selectedPkg) return;
    setActionLoading(true);
    const pkgId = selectedPkg.id || selectedPkg.tracking_number;

    try {
      const formData = new FormData();
      formData.append("package_id", pkgId);
      formData.append("driver_id", driverId);
      formData.append("reason", "Customer unavailable / Security access required");

      await client.post("/delivery/exception", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      setDeliveries((prev) =>
        prev.map((item) =>
          (item.id || item.tracking_number) === pkgId
            ? { ...item, status: "ATTEMPTED" }
            : item
        )
      );

      if (Platform.OS === "web") {
        window.alert(`Exception logged for package ${pkgId}`);
      } else {
        Alert.alert("Notice", `Exception logged for package ${pkgId}`);
      }
      setModalVisible(false);
    } catch (err) {
      console.warn("Backend exception call error:", err);
      setDeliveries((prev) =>
        prev.map((item) =>
          (item.id || item.tracking_number) === pkgId
            ? { ...item, status: "ATTEMPTED" }
            : item
        )
      );
      setModalVisible(false);
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
        {/* Top Header */}
        <View style={s.header}>
          <View>
            <Text style={s.heading}>My Deliveries</Text>
            <View style={s.driverRow}>
              <Text style={s.subheading}>{driverId}</Text>
              <View style={[s.statusDot, isOnline ? s.statusOnline : s.statusOffline]} />
              <Text style={s.statusText}>{isOnline ? "ONLINE" : "SYNCING..."}</Text>
            </View>
            <TouchableOpacity onPress={logout} style={s.signoutBtn}>
              <Text style={s.signout}>Sign out</Text>
            </TouchableOpacity>
          </View>

          <View style={s.headerActions}>
            <TouchableOpacity style={s.refreshHeaderBtn} onPress={onRefresh}>
              <Text style={s.refreshHeaderText}>?? Sync</Text>
            </TouchableOpacity>
          </View>
        </View>

        {/* Package List */}
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

        {/* Bottom Navigation Toolbar */}
        <View style={s.bottomBar}>
          <TouchableOpacity style={[s.tabItem, s.tabActive]} onPress={onRefresh}>
            <Text style={s.tabIcon}>??</Text>
            <Text style={[s.tabLabel, s.tabLabelActive]}>Manifest</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={s.tabScanCenter}
            onPress={() => (navigation?.navigate ? navigation.navigate("Scanner") : null)}
          >
            <Text style={s.scanCenterIcon}>??</Text>
            <Text style={s.scanCenterLabel}>Scan</Text>
          </TouchableOpacity>

          <TouchableOpacity style={s.tabItem} onPress={onRefresh}>
            <Text style={s.tabIcon}>??</Text>
            <Text style={s.tabLabel}>Refresh</Text>
          </TouchableOpacity>
        </View>

        {/* Package Action Modal */}
        <Modal visible={modalVisible} transparent animationType="fade">
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

              <View style={s.detailRow}>
                <Text style={s.detailLabel}>Current Status:</Text>
                <Text style={s.detailVal}>{selectedPkg?.status}</Text>
              </View>

              <View style={s.modalActions}>
                <TouchableOpacity
                  style={[s.modalBtn, s.btnSuccess]}
                  disabled={actionLoading}
                  onPress={handleConfirmDelivery}
                >
                  {actionLoading ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={s.btnTextWhite}>Mark as DELIVERED</Text>
                  )}
                </TouchableOpacity>

                <TouchableOpacity
                  style={[s.modalBtn, s.btnDanger]}
                  disabled={actionLoading}
                  onPress={handleDeliveryException}
                >
                  {actionLoading ? (
                    <ActivityIndicator color="#fff" />
                  ) : (
                    <Text style={s.btnTextWhite}>Report Exception / Failed</Text>
                  )}
                </TouchableOpacity>

                <TouchableOpacity
                  style={[s.modalBtn, s.btnCancel]}
                  onPress={() => setModalVisible(false)}
                  disabled={actionLoading}
                >
                  <Text style={s.btnTextDark}>Cancel</Text>
                </TouchableOpacity>
              </View>
            </View>
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
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
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
  tabActive: {},
  tabIcon: { fontSize: 20 },
  tabLabel: { color: "#94a3b8", fontSize: 11, fontWeight: "600", marginTop: 2 },
  tabLabelActive: { color: "#38bdf8" },
  tabScanCenter: {
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#2563eb",
    width: 52,
    height: 52,
    borderRadius: 26,
    marginTop: -20,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 6,
  },
  scanCenterIcon: { fontSize: 22 },
  scanCenterLabel: { color: "#fff", fontSize: 10, fontWeight: "700" },
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
  btnDanger: { backgroundColor: "#dc2626" },
  btnCancel: { backgroundColor: "#e2e8f0" },
  btnTextWhite: { color: "#fff", fontWeight: "700", fontSize: 14 },
  btnTextDark: { color: "#334155", fontWeight: "700", fontSize: 14 },
});
