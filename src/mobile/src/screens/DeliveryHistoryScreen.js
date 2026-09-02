import React, { useState, useEffect, useCallback } from "react";
import {
  StyleSheet,
  Text,
  View,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  SafeAreaView,
  Image,
  StatusBar,
  Platform,
  Alert,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import client from "../api/client";

export default function DeliveryHistoryScreen({ navigation }) {
  const [proofs, setProofs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showCsvBox, setShowCsvBox] = useState(false);
  const [csvText, setCsvText] = useState("");

  const baseUrl = client?.defaults?.baseURL || "http://10.0.2.2:8000";

  const loadProofs = useCallback(async () => {
    try {
      const response = await client.get("/delivery/recent-proofs", {
        params: { limit: 50 },
      });
      if (response && response.data) {
        setProofs(response.data);
      }
    } catch (err) {
      console.warn("[DeliveryHistory] Failed to load proofs:", err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadProofs();
    const unsubscribe = navigation.addListener("focus", () => {
      loadProofs();
    });
    return unsubscribe;
  }, [navigation, loadProofs]);

  const onRefresh = () => {
    setRefreshing(true);
    loadProofs();
  };

  const handleExportCSV = () => {
    if (!proofs || proofs.length === 0) {
      Alert.alert("No Data", "No delivery proofs available to export.");
      return;
    }

    const headers = [
      "id",
      "package_id",
      "driver_id",
      "status",
      "timestamp",
      "latitude",
      "longitude",
    ];

    const rows = proofs.map((p) => [
      p.id ?? "",
      `"${p.package_id || ""}"`,
      `"${p.driver_id || ""}"`,
      `"${p.status || ""}"`,
      `"${p.timestamp || ""}"`,
      p.dest_lat ?? p.latitude ?? "",
      p.dest_lon ?? p.longitude ?? "",
    ]);

    const formatted = [headers.join(","), ...rows.map((r) => r.join(","))].join("\n");
    setCsvText(formatted);
    setShowCsvBox(!showCsvBox);
  };

  const renderProofItem = ({ item }) => {
    const fullPhotoUrl = item.photo_url
      ? item.photo_url.startsWith("http")
        ? item.photo_url
        : `${baseUrl}${item.photo_url}`
      : null;

    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <View style={styles.packageBadge}>
            <MaterialCommunityIcons name="package-variant-closed" size={16} color="#38bdf8" />
            <Text style={styles.packageIdText}>{item.package_id}</Text>
          </View>
          <View style={styles.statusTag}>
            <Text style={styles.statusTagText}>{item.status}</Text>
          </View>
        </View>

        <View style={styles.cardBody}>
          <View style={styles.metaColumn}>
            <View style={styles.metaRow}>
              <MaterialCommunityIcons name="account-outline" size={15} color="#94a3b8" />
              <Text style={styles.metaText}>Driver: {item.driver_id}</Text>
            </View>

            <View style={styles.metaRow}>
              <MaterialCommunityIcons name="clock-outline" size={15} color="#94a3b8" />
              <Text style={styles.metaText}>
                {item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : "N/A"}
              </Text>
            </View>

            <View style={styles.metaRow}>
              <MaterialCommunityIcons name="map-marker-outline" size={15} color="#94a3b8" />
              <Text style={styles.metaText}>
                {Number(item.dest_lat).toFixed(4)}, {Number(item.dest_lon).toFixed(4)}
              </Text>
            </View>
          </View>

          {fullPhotoUrl ? (
            <Image source={{ uri: fullPhotoUrl }} style={styles.thumbnail} />
          ) : (
            <View style={styles.noPhotoThumbnail}>
              <MaterialCommunityIcons name="image-off-outline" size={20} color="#64748b" />
            </View>
          )}
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        {/* Top Header with Safe Top Padding */}
        <View style={styles.header}>
          <View style={{ flex: 1 }}>
            <Text style={styles.headerTitle}>Delivery Proof Log</Text>
            <Text style={styles.headerSubtitle}>
              {proofs.length} verified records in system
            </Text>
          </View>

          <View style={styles.headerActions}>
            <TouchableOpacity
              style={styles.exportButton}
              onPress={handleExportCSV}
              activeOpacity={0.6}
            >
              <MaterialCommunityIcons name="file-delimited-outline" size={16} color="#0f172a" />
              <Text style={styles.exportButtonText}>
                {showCsvBox ? "Hide CSV" : "Export CSV"}
              </Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.refreshButton} onPress={onRefresh}>
              <MaterialCommunityIcons name="refresh" size={20} color="#38bdf8" />
            </TouchableOpacity>
          </View>
        </View>

        {/* In-Line CSV Export Preview Box */}
        {showCsvBox && (
          <View style={styles.csvBox}>
            <View style={styles.csvBoxHeader}>
              <Text style={styles.csvBoxTitle}>Exported CSV Data ({proofs.length} rows)</Text>
              <TouchableOpacity onPress={() => setShowCsvBox(false)}>
                <MaterialCommunityIcons name="close" size={18} color="#94a3b8" />
              </TouchableOpacity>
            </View>
            <Text style={styles.csvText} selectable={true}>
              {csvText}
            </Text>
            <Text style={styles.copyNotice}>Tip: Long-press text above to copy.</Text>
          </View>
        )}

        {/* Proofs Feed */}
        {loading ? (
          <View style={styles.centerContainer}>
            <ActivityIndicator size="large" color="#38bdf8" />
            <Text style={styles.loadingText}>Fetching delivery records...</Text>
          </View>
        ) : (
          <FlatList
            data={proofs}
            keyExtractor={(item) => String(item.id)}
            renderItem={renderProofItem}
            contentContainerStyle={styles.listContent}
            refreshControl={
              <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#38bdf8" />
            }
          />
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#0f172a",
  },
  container: {
    flex: 1,
    paddingTop: Platform.OS === "android" ? StatusBar.currentHeight + 10 : 10,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingBottom: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#1e293b",
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: "800",
    color: "#f8fafc",
  },
  headerSubtitle: {
    fontSize: 12,
    color: "#94a3b8",
    marginTop: 2,
  },
  headerActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  exportButton: {
    backgroundColor: "#38bdf8",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  exportButtonText: {
    color: "#0f172a",
    fontSize: 12,
    fontWeight: "700",
  },
  refreshButton: {
    padding: 6,
  },
  csvBox: {
    margin: 16,
    padding: 14,
    backgroundColor: "#020617",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#38bdf8",
  },
  csvBoxHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  csvBoxTitle: {
    color: "#38bdf8",
    fontSize: 12,
    fontWeight: "700",
  },
  csvText: {
    fontFamily: "monospace",
    color: "#f1f5f9",
    fontSize: 11,
    lineHeight: 16,
    backgroundColor: "#0f172a",
    padding: 8,
    borderRadius: 6,
  },
  copyNotice: {
    color: "#64748b",
    fontSize: 10,
    marginTop: 6,
    textAlign: "right",
  },
  listContent: {
    padding: 16,
    gap: 12,
  },
  card: {
    backgroundColor: "#1e293b",
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: "#334155",
    gap: 12,
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  packageBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  packageIdText: {
    color: "#f8fafc",
    fontSize: 16,
    fontWeight: "700",
  },
  statusTag: {
    backgroundColor: "rgba(34, 197, 94, 0.15)",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: "rgba(34, 197, 94, 0.3)",
  },
  statusTagText: {
    color: "#4ade80",
    fontSize: 10,
    fontWeight: "700",
  },
  cardBody: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  metaColumn: {
    gap: 6,
    flex: 1,
  },
  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  metaText: {
    color: "#94a3b8",
    fontSize: 12,
  },
  thumbnail: {
    width: 64,
    height: 64,
    borderRadius: 8,
    backgroundColor: "#334155",
  },
  noPhotoThumbnail: {
    width: 64,
    height: 64,
    borderRadius: 8,
    backgroundColor: "#0f172a",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: "#334155",
  },
  centerContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingTop: 60,
    gap: 10,
  },
  loadingText: {
    color: "#94a3b8",
    fontSize: 14,
  },
});