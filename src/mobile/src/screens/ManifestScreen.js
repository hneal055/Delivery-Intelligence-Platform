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
  Alert,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import client from "../api/client";
import * as offlineQueueService from "../services/offlineQueueService";

export default function ManifestScreen({ navigation }) {
  const [stops, setStops] = useState([]);
  const [filter, setFilter] = useState("ALL"); // "ALL" | "PENDING" | "DELIVERED"
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Offline queue banner state
  const [pendingCount, setPendingCount] = useState(0);
  const [isSyncing, setIsSyncing] = useState(false);

  const baseUrl = client?.defaults?.baseURL || "http://localhost:8000";

  const checkPendingQueue = useCallback(async () => {
    try {
      const getCount =
        offlineQueueService?.getPendingQueueCount ||
        offlineQueueService?.default?.getPendingQueueCount;

      if (typeof getCount === "function") {
        const count = await getCount();
        setPendingCount(Number(count) || 0);
      }
    } catch (err) {
      console.warn("[ManifestScreen] Queue check error:", err?.message || err);
    }
  }, []);

  const loadManifest = useCallback(async () => {
    try {
      // 1. Fetch route stops for Driver D001
      const routeRes = await fetch(`${baseUrl}/routing/sample-route/D001`);
      const routeData = routeRes.ok ? await routeRes.json() : null;

      // 2. Fetch logged delivery proofs from persistent SQLite
      const proofsRes = await fetch(`${baseUrl}/delivery/recent-proofs?limit=50`);
      const proofsData = proofsRes.ok ? await proofsRes.json() : [];

      const deliveredPackageIds = new Set(
        proofsData
          .filter((p) => p.status === "DELIVERED")
          .map((p) => p.package_id)
      );

      const rawStops = routeData?.ordered_stops || [
        { id: "pkg-001", address: "100 N State St, Chicago, IL", lat: 41.8837, lon: -87.6278 },
        { id: "pkg-002", address: "231 S Michigan Ave, Chicago, IL", lat: 41.8789, lon: -87.6247 },
        { id: "pkg-003", address: "500 W Madison St, Chicago, IL", lat: 41.8819, lon: -87.6398 },
        { id: "pkg-004", address: "400 N Michigan Ave, Chicago, IL", lat: 41.8900, lon: -87.6240 },
        { id: "pkg-005", address: "222 W Merchandise Mart Plaza", lat: 41.8885, lon: -87.6354 },
      ];

      // Merge stop data with live status
      const unifiedStops = rawStops.map((stop, index) => {
        const isDelivered = deliveredPackageIds.has(stop.id);
        return {
          ...stop,
          stopNumber: index + 1,
          status: isDelivered ? "DELIVERED" : "PENDING",
        };
      });

      setStops(unifiedStops);
    } catch (err) {
      console.warn("[ManifestScreen] Failed to load manifest data:", err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [baseUrl]);

  useEffect(() => {
    loadManifest();
    checkPendingQueue();
    const unsubscribe = navigation.addListener("focus", () => {
      loadManifest();
      checkPendingQueue();
    });
    return unsubscribe;
  }, [navigation, loadManifest, checkPendingQueue]);

  const onRefresh = () => {
    setRefreshing(true);
    checkPendingQueue();
    loadManifest();
  };

  const handleManualSync = async () => {
    if (isSyncing || pendingCount === 0) return;

    const processQueue =
      offlineQueueService?.processOfflineQueue ||
      offlineQueueService?.default?.processOfflineQueue;

    if (typeof processQueue !== "function") {
      Alert.alert("Sync Error", "Offline queue service function is not available.");
      return;
    }

    setIsSyncing(true);
    try {
      const result = await processQueue();
      await checkPendingQueue();
      await loadManifest();

      const synced = result?.syncedCount ?? 0;
      const failed = result?.failedCount ?? 0;

      if (synced > 0 && failed === 0) {
        Alert.alert(
          "Sync Succeeded",
          `Successfully uploaded ${synced} queued proof${synced > 1 ? "s" : ""}.`
        );
      } else if (synced > 0 && failed > 0) {
        Alert.alert(
          "Partial Sync",
          `Uploaded ${synced} proof(s), but ${failed} remain queued.`
        );
      } else if (failed > 0) {
        Alert.alert(
          "Sync Failed",
          "Could not reach backend. Queued deliveries remain saved locally."
        );
      }
    } catch (err) {
      Alert.alert("Sync Error", "An error occurred during sync attempt.");
    } finally {
      setIsSyncing(false);
    }
  };

  const filteredStops = stops.filter((stop) => {
    if (filter === "PENDING") return stop.status === "PENDING";
    if (filter === "DELIVERED") return stop.status === "DELIVERED";
    return true;
  });

  const counts = {
    all: stops.length,
    pending: stops.filter((s) => s.status === "PENDING").length,
    delivered: stops.filter((s) => s.status === "DELIVERED").length,
  };

  const renderStopItem = ({ item }) => {
    const isDelivered = item.status === "DELIVERED";

    return (
      <View style={[styles.stopCard, isDelivered && styles.deliveredCard]}>
        <View style={[styles.stopBadge, isDelivered && styles.deliveredBadge]}>
          {isDelivered ? (
            <MaterialCommunityIcons name="check-bold" size={18} color="#ffffff" />
          ) : (
            <Text style={styles.stopNumberText}>{item.stopNumber}</Text>
          )}
        </View>

        <View style={styles.stopDetails}>
          <View style={styles.stopTopRow}>
            <Text style={styles.packageIdText}>{item.id}</Text>
            <View
              style={[
                styles.statusTag,
                isDelivered ? styles.deliveredTag : styles.pendingTag,
              ]}
            >
              <Text
                style={[
                  styles.statusTagText,
                  isDelivered ? styles.deliveredTagText : styles.pendingTagText,
                ]}
              >
                {item.status}
              </Text>
            </View>
          </View>

          <Text style={styles.addressText} numberOfLines={2}>
            {item.address}
          </Text>

          <View style={styles.coordsRow}>
            <MaterialCommunityIcons name="map-marker-outline" size={14} color="#94a3b8" />
            <Text style={styles.coordsText}>
              {Number(item.lat).toFixed(4)}, {Number(item.lon).toFixed(4)}
            </Text>
          </View>
        </View>

        {!isDelivered ? (
          <TouchableOpacity
            style={styles.actionButton}
            onPress={() => navigation.navigate("Scanner", { packageId: item.id })}
          >
            <MaterialCommunityIcons name="barcode-scan" size={18} color="#ffffff" />
            <Text style={styles.actionButtonText}>Scan</Text>
          </TouchableOpacity>
        ) : (
          <TouchableOpacity
            style={styles.proofsButton}
            onPress={() => navigation.navigate("ProofsTab")}
          >
            <MaterialCommunityIcons name="image-outline" size={18} color="#38bdf8" />
          </TouchableOpacity>
        )}
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>Route Manifest</Text>
          <Text style={styles.headerSubtitle}>
            Driver D001 • {counts.pending} stops remaining
          </Text>
        </View>
        <TouchableOpacity style={styles.refreshIconButton} onPress={onRefresh}>
          <MaterialCommunityIcons name="refresh" size={22} color="#38bdf8" />
        </TouchableOpacity>
      </View>

      {/* Inline Offline Sync Indicator */}
      {pendingCount > 0 && (
        <View style={styles.offlineAlertBanner}>
          <View style={styles.offlineBannerLeft}>
            <MaterialCommunityIcons name="cloud-sync-outline" size={22} color="#f59e0b" />
            <View style={styles.offlineTextColumn}>
              <View style={styles.offlineTitleRow}>
                <Text style={styles.offlineBannerTitle}>Offline Queued</Text>
                <View style={styles.offlineBadge}>
                  <Text style={styles.offlineBadgeText}>{pendingCount}</Text>
                </View>
              </View>
              <Text style={styles.offlineBannerSubtitle}>
                {pendingCount === 1 ? "1 delivery proof" : `${pendingCount} delivery proofs`} awaiting upload
              </Text>
            </View>
          </View>
          <TouchableOpacity
            style={[styles.syncButton, isSyncing && styles.disabledButton]}
            onPress={handleManualSync}
            disabled={isSyncing}
          >
            {isSyncing ? (
              <ActivityIndicator size="small" color="#0f172a" />
            ) : (
              <Text style={styles.syncButtonText}>Sync</Text>
            )}
          </TouchableOpacity>
        </View>
      )}

      {/* Filter Chips */}
      <View style={styles.filterRow}>
        <TouchableOpacity
          style={[styles.filterChip, filter === "ALL" && styles.activeFilterChip]}
          onPress={() => setFilter("ALL")}
        >
          <Text style={[styles.filterChipText, filter === "ALL" && styles.activeFilterChipText]}>
            All ({counts.all})
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.filterChip, filter === "PENDING" && styles.activeFilterChip]}
          onPress={() => setFilter("PENDING")}
        >
          <Text style={[styles.filterChipText, filter === "PENDING" && styles.activeFilterChipText]}>
            Pending ({counts.pending})
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.filterChip, filter === "DELIVERED" && styles.activeFilterChip]}
          onPress={() => setFilter("DELIVERED")}
        >
          <Text style={[styles.filterChipText, filter === "DELIVERED" && styles.activeFilterChipText]}>
            Delivered ({counts.delivered})
          </Text>
        </TouchableOpacity>
      </View>

      {/* Main List */}
      {loading ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color="#38bdf8" />
          <Text style={styles.loadingText}>Sequencing route stops...</Text>
        </View>
      ) : (
        <FlatList
          data={filteredStops}
          keyExtractor={(item) => item.id}
          renderItem={renderStopItem}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#38bdf8" />
          }
          ListEmptyComponent={
            <View style={styles.centerContainer}>
              <MaterialCommunityIcons name="check-all" size={48} color="#475569" />
              <Text style={styles.emptyTitle}>No stops match filter</Text>
              <Text style={styles.emptySubtitle}>
                Select another filter tab or refresh route data.
              </Text>
            </View>
          }
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0f172a",
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
    fontSize: 20,
    fontWeight: "800",
    color: "#f8fafc",
  },
  headerSubtitle: {
    fontSize: 12,
    color: "#94a3b8",
    marginTop: 2,
  },
  refreshIconButton: {
    padding: 6,
  },
  offlineAlertBanner: {
    backgroundColor: "#1e293b",
    borderColor: "rgba(245, 158, 11, 0.4)",
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginHorizontal: 16,
    marginTop: 10,
    marginBottom: 4,
  },
  offlineBannerLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    flex: 1,
  },
  offlineTextColumn: {
    flex: 1,
  },
  offlineTitleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  offlineBannerTitle: {
    color: "#f59e0b",
    fontSize: 14,
    fontWeight: "700",
  },
  offlineBadge: {
    backgroundColor: "#f59e0b",
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 10,
  },
  offlineBadgeText: {
    color: "#0f172a",
    fontSize: 11,
    fontWeight: "800",
  },
  offlineBannerSubtitle: {
    color: "#94a3b8",
    fontSize: 11,
    marginTop: 2,
  },
  syncButton: {
    backgroundColor: "#f59e0b",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 6,
    minWidth: 60,
    alignItems: "center",
  },
  syncButtonText: {
    color: "#0f172a",
    fontWeight: "700",
    fontSize: 12,
  },
  disabledButton: {
    opacity: 0.6,
  },
  filterRow: {
    flexDirection: "row",
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 8,
  },
  filterChip: {
    backgroundColor: "#1e293b",
    paddingVertical: 6,
    paddingHorizontal: 14,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: "#334155",
  },
  activeFilterChip: {
    backgroundColor: "#2563eb",
    borderColor: "#38bdf8",
  },
  filterChipText: {
    color: "#94a3b8",
    fontSize: 12,
    fontWeight: "600",
  },
  activeFilterChipText: {
    color: "#ffffff",
  },
  listContent: {
    padding: 16,
    gap: 12,
  },
  stopCard: {
    backgroundColor: "#1e293b",
    borderRadius: 12,
    padding: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderWidth: 1,
    borderColor: "#334155",
  },
  deliveredCard: {
    opacity: 0.75,
    borderColor: "rgba(34, 197, 94, 0.3)",
  },
  stopBadge: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#2563eb",
    alignItems: "center",
    justifyContent: "center",
  },
  deliveredBadge: {
    backgroundColor: "#16a34a",
  },
  stopNumberText: {
    color: "#ffffff",
    fontWeight: "800",
    fontSize: 14,
  },
  stopDetails: {
    flex: 1,
  },
  stopTopRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 4,
  },
  packageIdText: {
    fontSize: 15,
    fontWeight: "700",
    color: "#f8fafc",
  },
  statusTag: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
  },
  pendingTag: {
    backgroundColor: "rgba(234, 179, 8, 0.15)",
    borderWidth: 1,
    borderColor: "rgba(234, 179, 8, 0.3)",
  },
  pendingTagText: {
    color: "#facc15",
    fontSize: 10,
    fontWeight: "700",
  },
  deliveredTag: {
    backgroundColor: "rgba(34, 197, 94, 0.15)",
    borderWidth: 1,
    borderColor: "rgba(34, 197, 94, 0.3)",
  },
  deliveredTagText: {
    color: "#4ade80",
    fontSize: 10,
    fontWeight: "700",
  },
  addressText: {
    color: "#cbd5e1",
    fontSize: 13,
    fontWeight: "500",
    marginBottom: 4,
  },
  coordsRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  coordsText: {
    fontSize: 11,
    color: "#94a3b8",
  },
  actionButton: {
    backgroundColor: "#16a34a",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  actionButtonText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 12,
  },
  proofsButton: {
    backgroundColor: "rgba(56, 189, 248, 0.15)",
    padding: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "rgba(56, 189, 248, 0.3)",
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
  emptyTitle: {
    fontSize: 16,
    fontWeight: "600",
    color: "#cbd5e1",
  },
  emptySubtitle: {
    fontSize: 13,
    color: "#64748b",
    textAlign: "center",
    maxWidth: 240,
  },
});