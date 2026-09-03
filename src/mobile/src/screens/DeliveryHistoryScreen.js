import React, { useState, useEffect, useCallback } from "react";
import {
  StyleSheet,
  Text,
  View,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import client from "../api/client";

export default function DeliveryHistoryScreen({ navigation }) {
  const [proofs, setProofs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [csvContent, setCsvContent] = useState(null);
  const [isExporting, setIsExporting] = useState(false);

  const fetchProofs = useCallback(async () => {
    try {
      const res = await client.get("/delivery/recent-proofs", {
        params: { limit: 50 },
      });
      if (res && Array.isArray(res.data)) {
        setProofs(res.data);
      }
    } catch (err) {
      console.warn("[DeliveryHistoryScreen] Failed to fetch proofs:", err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchProofs();
    const unsubscribe = navigation.addListener("focus", () => {
      fetchProofs();
    });
    return unsubscribe;
  }, [navigation, fetchProofs]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchProofs();
  };

  const handleToggleExport = async () => {
    if (csvContent) {
      setCsvContent(null);
      return;
    }

    setIsExporting(true);
    try {
      const res = await client.get("/delivery/export", {
        params: { format: "csv" },
        responseType: "text",
      });

      if (res.data) {
        setCsvContent(res.data);
      } else {
        Alert.alert("Export Notice", "No verified delivery records available to export.");
      }
    } catch (err) {
      Alert.alert("Export Error", "Could not fetch CSV export from backend.");
    } finally {
      setIsExporting(false);
    }
  };

  const renderProofCard = ({ item }) => {
    const formattedTime = item.timestamp
      ? new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
      : "Pending Time";

    return (
      <View style={styles.card}>
        <View style={styles.cardHeaderRow}>
          <View style={styles.titleGroup}>
            <MaterialCommunityIcons name="cube-outline" size={18} color="#38bdf8" />
            <Text style={styles.packageId}>{item.package_id}</Text>
          </View>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>{item.status || "DELIVERED"}</Text>
          </View>
        </View>

        <View style={styles.metaRow}>
          <MaterialCommunityIcons name="account-outline" size={15} color="#94a3b8" />
          <Text style={styles.metaText}>Driver: {item.driver_id}</Text>
        </View>

        <View style={styles.metaRow}>
          <MaterialCommunityIcons name="clock-outline" size={15} color="#94a3b8" />
          <Text style={styles.metaText}>{formattedTime}</Text>
        </View>

        <View style={styles.metaRow}>
          <MaterialCommunityIcons name="map-marker-outline" size={15} color="#94a3b8" />
          <Text style={styles.metaText}>
            {item.latitude ? item.latitude.toFixed(4) : "41.8819"},{" "}
            {item.longitude ? item.longitude.toFixed(4) : "-87.6398"}
          </Text>
        </View>

        <View style={styles.photoContainer}>
          <View style={styles.photoPlaceholder}>
            <MaterialCommunityIcons name="image-off-outline" size={24} color="#475569" />
          </View>
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <View style={styles.header}>
          <View>
            <Text style={styles.headerTitle}>Delivery Proof Log</Text>
            <Text style={styles.headerSubtitle}>{proofs.length} verified records in system</Text>
          </View>
          <View style={styles.headerActions}>
            <TouchableOpacity
              style={[styles.exportButton, csvContent && styles.exportButtonActive]}
              onPress={handleToggleExport}
              disabled={isExporting}
              activeOpacity={0.7}
            >
              {isExporting ? (
                <ActivityIndicator size="small" color="#38bdf8" />
              ) : (
                <>
                  <MaterialCommunityIcons
                    name={csvContent ? "eye-off-outline" : "file-delimited-outline"}
                    size={16}
                    color={csvContent ? "#ffffff" : "#38bdf8"}
                  />
                  <Text style={[styles.exportButtonText, csvContent && styles.exportButtonTextActive]}>
                    {csvContent ? "Hide CSV" : "Export CSV"}
                  </Text>
                </>
              )}
            </TouchableOpacity>

            <TouchableOpacity onPress={onRefresh} style={styles.refreshIconButton} activeOpacity={0.7}>
              <MaterialCommunityIcons name="refresh" size={22} color="#38bdf8" />
            </TouchableOpacity>
          </View>
        </View>

        {csvContent ? (
          <View style={styles.csvContainer}>
            <View style={styles.csvHeader}>
              <Text style={styles.csvTitle}>Exported CSV Data ({proofs.length} rows)</Text>
              <TouchableOpacity onPress={() => setCsvContent(null)}>
                <MaterialCommunityIcons name="close" size={18} color="#94a3b8" />
              </TouchableOpacity>
            </View>
            <Text style={styles.csvText} selectable={true}>
              {csvContent}
            </Text>
            <Text style={styles.csvHint}>Tip: Long-press text above to copy.</Text>
          </View>
        ) : null}

        {loading && !refreshing ? (
          <View style={styles.centered}>
            <ActivityIndicator size="large" color="#38bdf8" />
          </View>
        ) : (
          <FlatList
            data={proofs}
            keyExtractor={(item) => String(item.id || item.package_id)}
            renderItem={renderProofCard}
            contentContainerStyle={styles.listContent}
            refreshControl={
              <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#38bdf8" />
            }
            ListEmptyComponent={
              <View style={styles.emptyContainer}>
                <MaterialCommunityIcons name="clipboard-text-outline" size={48} color="#475569" />
                <Text style={styles.emptyText}>No verified proofs found yet.</Text>
              </View>
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
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: "#1e293b",
  },
  headerTitle: {
    fontSize: 22,
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
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: "rgba(56, 189, 248, 0.1)",
    borderWidth: 1,
    borderColor: "rgba(56, 189, 248, 0.3)",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
  },
  exportButtonActive: {
    backgroundColor: "#2563eb",
    borderColor: "#38bdf8",
  },
  exportButtonText: {
    color: "#38bdf8",
    fontSize: 12,
    fontWeight: "700",
  },
  exportButtonTextActive: {
    color: "#ffffff",
  },
  refreshIconButton: {
    padding: 6,
  },
  csvContainer: {
    margin: 16,
    padding: 14,
    backgroundColor: "#090d16",
    borderRadius: 10,
    borderWidth: 1,
    borderColor: "#1e293b",
    gap: 8,
  },
  csvHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  csvTitle: {
    color: "#38bdf8",
    fontSize: 12,
    fontWeight: "700",
  },
  csvText: {
    fontFamily: "monospace",
    color: "#cbd5e1",
    fontSize: 11,
    lineHeight: 16,
    backgroundColor: "#0f172a",
    padding: 10,
    borderRadius: 6,
  },
  csvHint: {
    color: "#64748b",
    fontSize: 10,
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
    gap: 6,
    position: "relative",
  },
  cardHeaderRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 4,
  },
  titleGroup: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  packageId: {
    fontSize: 16,
    fontWeight: "800",
    color: "#f8fafc",
  },
  badge: {
    backgroundColor: "rgba(74, 222, 128, 0.15)",
    borderWidth: 1,
    borderColor: "rgba(74, 222, 128, 0.3)",
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  badgeText: {
    color: "#4ade80",
    fontSize: 10,
    fontWeight: "700",
  },
  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  metaText: {
    fontSize: 12,
    color: "#94a3b8",
  },
  photoContainer: {
    position: "absolute",
    right: 14,
    bottom: 14,
  },
  photoPlaceholder: {
    width: 44,
    height: 44,
    borderRadius: 8,
    backgroundColor: "#0f172a",
    borderWidth: 1,
    borderColor: "#334155",
    alignItems: "center",
    justifyContent: "center",
  },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  emptyContainer: {
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 40,
    gap: 12,
  },
  emptyText: {
    color: "#64748b",
    fontSize: 14,
  },
});
