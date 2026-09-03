import React, { useState, useEffect, useCallback } from "react";
import {
  StyleSheet,
  Text,
  View,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import client from "../api/client";

const INITIAL_STOPS = [
  { id: "1", packageId: "pkg-001", address: "100 N State St, Chicago, IL", lat: 41.8837, lon: -87.6278, status: "PENDING" },
  { id: "2", packageId: "pkg-002", address: "231 S Michigan Ave, Chicago, IL", lat: 41.8789, lon: -87.6247, status: "PENDING" },
  { id: "3", packageId: "pkg-003", address: "500 W Madison St, Chicago, IL", lat: 41.8819, lon: -87.6398, status: "PENDING" },
  { id: "4", packageId: "pkg-004", address: "400 N Michigan Ave, Chicago, IL", lat: 41.8900, lon: -87.6240, status: "PENDING" },
  { id: "5", packageId: "pkg-005", address: "222 W Merchandise Mart Plaza", lat: 41.8885, lon: -87.6354, status: "PENDING" },
];

export default function ManifestScreen({ navigation }) {
  const [stops, setStops] = useState(INITIAL_STOPS);
  const [filter, setFilter] = useState("ALL");
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const syncManifestWithBackend = useCallback(async () => {
    try {
      const res = await client.get("/delivery/recent-proofs", { params: { limit: 50 } });
      if (res && Array.isArray(res.data)) {
        const deliveredIds = new Set(res.data.map((item) => item.package_id));
        setStops((prevStops) =>
          prevStops.map((stop) => ({
            ...stop,
            status: deliveredIds.has(stop.packageId) ? "DELIVERED" : "PENDING",
          }))
        );
      }
    } catch (_) {
      // Keep local state on network error
    } finally {
      setRefreshing(false);
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    syncManifestWithBackend();
    const unsubscribe = navigation.addListener("focus", () => {
      syncManifestWithBackend();
    });
    return unsubscribe;
  }, [navigation, syncManifestWithBackend]);

  const onRefresh = () => {
    setRefreshing(true);
    syncManifestWithBackend();
  };

  const pendingCount = stops.filter((s) => s.status === "PENDING").length;
  const deliveredCount = stops.filter((s) => s.status === "DELIVERED").length;

  const filteredStops = stops.filter((stop) => {
    if (filter === "PENDING") return stop.status === "PENDING";
    if (filter === "DELIVERED") return stop.status === "DELIVERED";
    return true;
  });

  const renderStopItem = ({ item }) => {
    const isDelivered = item.status === "DELIVERED";

    return (
      <View style={[styles.card, isDelivered && styles.cardDelivered]}>
        <View style={styles.cardHeaderRow}>
          <View style={[styles.indexCircle, isDelivered && styles.indexCircleDelivered]}>
            {isDelivered ? (
              <MaterialCommunityIcons name="check" size={18} color="#ffffff" />
            ) : (
              <Text style={styles.indexText}>{item.id}</Text>
            )}
          </View>

          <View style={styles.headerDetails}>
            <View style={styles.titleRow}>
              <MaterialCommunityIcons
                name={isDelivered ? "package-variant-closed-check" : "package-variant-closed"}
                size={16}
                color={isDelivered ? "#4ade80" : "#38bdf8"}
              />
              <Text style={styles.packageIdText}>{item.packageId}</Text>
              <View style={[styles.badge, isDelivered ? styles.badgeDelivered : styles.badgePending]}>
                <Text style={[styles.badgeText, isDelivered ? styles.badgeTextDelivered : styles.badgeTextPending]}>
                  {item.status}
                </Text>
              </View>
            </View>
            <Text style={styles.addressText}>{item.address}</Text>
            <View style={styles.coordsRow}>
              <MaterialCommunityIcons name="map-marker-outline" size={13} color="#64748b" />
              <Text style={styles.coordsText}>{item.lat.toFixed(4)}, {item.lon.toFixed(4)}</Text>
            </View>
          </View>

          <View style={styles.cardActionContainer}>
            {isDelivered ? (
              <TouchableOpacity
                style={styles.photoViewButton}
                onPress={() => navigation.navigate("Proofs")}
                activeOpacity={0.7}
              >
                <MaterialCommunityIcons name="image-outline" size={18} color="#38bdf8" />
              </TouchableOpacity>
            ) : (
              <TouchableOpacity
                style={styles.scanButton}
                onPress={() => navigation.navigate("Scanner", { packageId: item.packageId })}
                activeOpacity={0.7}
              >
                <MaterialCommunityIcons name="barcode-scan" size={16} color="#ffffff" />
                <Text style={styles.scanButtonText}>Scan</Text>
              </TouchableOpacity>
            )}
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
            <Text style={styles.headerTitle}>Route Manifest</Text>
            <Text style={styles.headerSubtitle}>Driver D001 • {pendingCount} stops remaining</Text>
          </View>
          <TouchableOpacity onPress={onRefresh} style={styles.refreshIconButton} activeOpacity={0.7}>
            <MaterialCommunityIcons name="refresh" size={22} color="#38bdf8" />
          </TouchableOpacity>
        </View>

        <View style={styles.filterRow}>
          <TouchableOpacity
            style={[styles.filterPill, filter === "ALL" && styles.filterPillActive]}
            onPress={() => setFilter("ALL")}
          >
            <Text style={[styles.filterText, filter === "ALL" && styles.filterTextActive]}>
              All ({stops.length})
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.filterPill, filter === "PENDING" && styles.filterPillActive]}
            onPress={() => setFilter("PENDING")}
          >
            <Text style={[styles.filterText, filter === "PENDING" && styles.filterTextActive]}>
              Pending ({pendingCount})
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.filterPill, filter === "DELIVERED" && styles.filterPillActive]}
            onPress={() => setFilter("DELIVERED")}
          >
            <Text style={[styles.filterText, filter === "DELIVERED" && styles.filterTextActive]}>
              Delivered ({deliveredCount})
            </Text>
          </TouchableOpacity>
        </View>

        {loading && !refreshing ? (
          <View style={styles.centered}>
            <ActivityIndicator size="large" color="#38bdf8" />
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
  refreshIconButton: {
    padding: 6,
  },
  filterRow: {
    flexDirection: "row",
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 8,
  },
  filterPill: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
    backgroundColor: "#1e293b",
    borderWidth: 1,
    borderColor: "#334155",
  },
  filterPillActive: {
    backgroundColor: "#2563eb",
    borderColor: "#38bdf8",
  },
  filterText: {
    fontSize: 12,
    color: "#94a3b8",
    fontWeight: "600",
  },
  filterTextActive: {
    color: "#ffffff",
    fontWeight: "700",
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
  },
  cardDelivered: {
    borderColor: "rgba(74, 222, 128, 0.3)",
    backgroundColor: "rgba(30, 41, 59, 0.7)",
  },
  cardHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  indexCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#2563eb",
    alignItems: "center",
    justifyContent: "center",
  },
  indexCircleDelivered: {
    backgroundColor: "#16a34a",
  },
  indexText: {
    color: "#ffffff",
    fontSize: 14,
    fontWeight: "700",
  },
  headerDetails: {
    flex: 1,
    gap: 3,
  },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  packageIdText: {
    color: "#f8fafc",
    fontSize: 14,
    fontWeight: "700",
  },
  badge: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    marginLeft: "auto",
  },
  badgePending: {
    backgroundColor: "rgba(251, 191, 36, 0.15)",
    borderWidth: 1,
    borderColor: "rgba(251, 191, 36, 0.3)",
  },
  badgeDelivered: {
    backgroundColor: "rgba(74, 222, 128, 0.15)",
    borderWidth: 1,
    borderColor: "rgba(74, 222, 128, 0.3)",
  },
  badgeText: {
    fontSize: 10,
    fontWeight: "700",
  },
  badgeTextPending: {
    color: "#fbbf24",
  },
  badgeTextDelivered: {
    color: "#4ade80",
  },
  addressText: {
    color: "#cbd5e1",
    fontSize: 12,
    fontWeight: "500",
  },
  coordsRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  coordsText: {
    color: "#64748b",
    fontSize: 11,
  },
  cardActionContainer: {
    marginLeft: 4,
  },
  scanButton: {
    backgroundColor: "#16a34a",
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  scanButtonText: {
    color: "#ffffff",
    fontSize: 12,
    fontWeight: "700",
  },
  photoViewButton: {
    width: 38,
    height: 38,
    borderRadius: 8,
    backgroundColor: "rgba(56, 189, 248, 0.1)",
    borderWidth: 1,
    borderColor: "rgba(56, 189, 248, 0.25)",
    alignItems: "center",
    justifyContent: "center",
  },
  centered: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
});