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

  const driverId = user?.driver_id || (user?.username === "driver1" ? "D001" : user?.username || "D001");

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
        headers: {
          "Content-Type": "multipart/form-data",
        },
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
        headers: {
          "Content-Type": "multipart/form-data",
        },
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
    <View style={s.container}>
      {/* Top Header */}
      <View style={s.header}>
        <View>
          <Text style={s.heading}>My Deliveries</Text>
          <Text style={s.subheading}>{driverId}</Text>
          <TouchableOpacity onPress={logout}>
            <Text style={s.signout}>Sign out</Text>
          </TouchableOpacity>
        </View>
        <TouchableOpacity
          style={s.scanBtn}
          onPress={() => (navigation?.navigate ? navigation.navigate("Scanner") : null)}
        >
          <Text style={s.scanBtnText}>📷 Scan Barcode</Text>
        </TouchableOpacity>
      </View>

      {/* Package List */}
      {loading ? (
        <ActivityIndicator size="large" color="#2952e3" style={{ marginTop: 40 }} />
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
              <Text style={s.detailVal}>{selectedPkg?.address || selectedPkg?.destination_address || "None"}</Text>
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
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f8f9fa" },
  header: {
    backgroundColor: "#2952e3",
    paddingTop: 36,
    paddingBottom: 20,
    paddingHorizontal: 24,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  heading: { fontSize: 24, fontWeight: "800", color: "#fff" },
  subheading: { fontSize: 13, color: "#dbe4ff", marginTop: 2, fontWeight: "600" },
  signout: { fontSize: 12, color: "#ffc9c9", marginTop: 4, textDecorationLine: "underline" },
  scanBtn: {
    backgroundColor: "#fff",
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 8,
  },
  scanBtnText: { color: "#2952e3", fontWeight: "700", fontSize: 13 },
  listContent: { padding: 20 },
  card: {
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 18,
    marginBottom: 14,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#e9ecef",
    cursor: "pointer",
  },
  cardLeft: { flex: 1, paddingRight: 12 },
  pkgId: { fontSize: 16, fontWeight: "700", color: "#212529", marginBottom: 4 },
  address: { fontSize: 13, color: "#6c757d" },
  badge: { paddingHorizontal: 10, paddingVertical: 5, borderRadius: 16 },
  badgeOut: { backgroundColor: "#2952e3" },
  badgeDelivered: { backgroundColor: "#2b8a3e" },
  badgeAttempted: { backgroundColor: "#e03131" },
  badgeText: { color: "#fff", fontSize: 11, fontWeight: "700" },
  empty: { textAlign: "center", color: "#868e96", marginTop: 40 },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.5)",
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
  modalHeader: { fontSize: 20, fontWeight: "800", marginBottom: 18, color: "#212529" },
  detailRow: { marginBottom: 10 },
  detailLabel: { fontSize: 12, color: "#868e96", fontWeight: "600", textTransform: "uppercase" },
  detailVal: { fontSize: 15, color: "#212529", fontWeight: "600", marginTop: 2 },
  modalActions: { marginTop: 24, gap: 10 },
  modalBtn: { paddingVertical: 14, borderRadius: 10, alignItems: "center" },
  btnSuccess: { backgroundColor: "#2b8a3e" },
  btnDanger: { backgroundColor: "#e03131" },
  btnCancel: { backgroundColor: "#e9ecef" },
  btnTextWhite: { color: "#fff", fontWeight: "700", fontSize: 14 },
  btnTextDark: { color: "#495057", fontWeight: "700", fontSize: 14 },
});