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
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import client from "../api/client";

export default function ManifestScreen({ navigation }) {
  const [stops, setStops] = useState([]);
  const [filter, setFilter] = useState("ALL"); // "ALL" | "PENDING" | "DELIVERED"
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const baseUrl = client?.defaults?.baseURL || "http://localhost:8000";

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
    const unsubscribe = navigation.addListener("focus", () => {
      loadManifest();
    });
    return unsubscribe;
  }, [navigation, loadManifest]);

  const onRefresh = () => {
    setRefreshing(true);
    loadManifest();
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