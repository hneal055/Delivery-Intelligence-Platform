import React, { useState, useEffect, useCallback } from "react";
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ScrollView,
  SafeAreaView,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import { useAuthStore } from "../stores/authStore";
import * as offlineQueueService from "../services/offlineQueueService";

export default function HomeScreen({ navigation }) {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  const [pendingCount, setPendingCount] = useState(0);
  const [isSyncing, setIsSyncing] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

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
      console.warn("[HomeScreen] Queue check error:", err?.message || err);
    }
  }, []);

  useEffect(() => {
    checkPendingQueue();
    const unsubscribe = navigation.addListener("focus", () => {
      checkPendingQueue();
    });
    return unsubscribe;
  }, [navigation, checkPendingQueue]);

  const onRefresh = async () => {
    setRefreshing(true);
    await checkPendingQueue();
    setRefreshing(false);
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

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView
        contentContainerStyle={styles.container}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#38bdf8" />
        }
      >
        {/* Top Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.driverGreeting}>Driver Portal</Text>
            <Text style={styles.driverName}>
              {user?.username || user?.email || "Driver D001"}
            </Text>
          </View>
          <TouchableOpacity style={styles.logoutButton} onPress={logout}>
            <MaterialCommunityIcons name="logout-variant" size={20} color="#ef4444" />
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

        {/* Route Overview Metric Cards */}
        <View style={styles.statsRow}>
          <View style={styles.statCard}>
            <MaterialCommunityIcons name="truck-delivery-outline" size={24} color="#38bdf8" />
            <Text style={styles.statNumber}>18</Text>
            <Text style={styles.statLabel}>Assigned</Text>
          </View>

          <View style={styles.statCard}>
            <MaterialCommunityIcons name="check-decagram-outline" size={24} color="#4ade80" />
            <Text style={styles.statNumber}>14</Text>
            <Text style={styles.statLabel}>Completed</Text>
          </View>

          <View style={styles.statCard}>
            <MaterialCommunityIcons name="clock-time-four-outline" size={24} color="#fbbf24" />
            <Text style={styles.statNumber}>4</Text>
            <Text style={styles.statLabel}>Remaining</Text>
          </View>
        </View>

        {/* Primary Action: Launch Scanner */}
        <TouchableOpacity
          style={styles.primaryActionCard}
          onPress={() => navigation.navigate("Scanner")}
        >
          <View style={styles.actionIconContainer}>
            <MaterialCommunityIcons name="barcode-scan" size={32} color="#ffffff" />
          </View>
          <View style={styles.actionTextContainer}>
            <Text style={styles.primaryActionTitle}>Scan & Confirm Delivery</Text>
            <Text style={styles.primaryActionSubtitle}>
              Capture package barcode, photo proof, and signature
            </Text>
          </View>
          <MaterialCommunityIcons name="chevron-right" size={24} color="#94a3b8" />
        </TouchableOpacity>

        {/* Secondary Action: Delivery Proof Log */}
        <TouchableOpacity
          style={styles.secondaryActionCard}
          onPress={() => navigation.navigate("ProofsTab")}
        >
          <View style={[styles.actionIconContainer, styles.historyIconContainer]}>
            <MaterialCommunityIcons name="clipboard-check-outline" size={28} color="#38bdf8" />
          </View>
          <View style={styles.actionTextContainer}>
            <Text style={styles.secondaryActionTitle}>Delivery Proof Log</Text>
            <Text style={styles.secondaryActionSubtitle}>
              Inspect recent delivery photos, timestamps, and coordinates
            </Text>
          </View>
          <MaterialCommunityIcons name="chevron-right" size={24} color="#94a3b8" />
        </TouchableOpacity>

        {/* Up Next on Route */}
        <View style={styles.sectionHeader}>
          <Text style={styles.sectionTitle}>Up Next on Route</Text>
        </View>

        <View style={styles.stopCard}>
          <View style={styles.stopBadge}>
            <Text style={styles.stopNumber}>15</Text>
          </View>
          <View style={styles.stopDetails}>
            <Text style={styles.stopAddress}>100 N State St, Chicago, IL</Text>
            <Text style={styles.stopPackage}>Package: pkg-001 (Priority)</Text>
          </View>
          <TouchableOpacity
            style={styles.deliverStopButton}
            onPress={() => navigation.navigate("Scanner", { packageId: "pkg-001" })}
          >
            <Text style={styles.deliverStopButtonText}>Deliver</Text>
          </TouchableOpacity>
        </View>

        <View style={styles.stopCard}>
          <View style={styles.stopBadge}>
            <Text style={styles.stopNumber}>16</Text>
          </View>
          <View style={styles.stopDetails}>
            <Text style={styles.stopAddress}>231 S Michigan Ave, Chicago, IL</Text>
            <Text style={styles.stopPackage}>Package: pkg-002 (Standard)</Text>
          </View>
          <TouchableOpacity
            style={styles.deliverStopButton}
            onPress={() => navigation.navigate("Scanner", { packageId: "pkg-002" })}
          >
            <Text style={styles.deliverStopButtonText}>Deliver</Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#0f172a",
  },
  container: {
    padding: 20,
    gap: 16,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 8,
    marginBottom: 4,
  },
  driverGreeting: {
    fontSize: 13,
    color: "#94a3b8",
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 0.8,
  },
  driverName: {
    fontSize: 22,
    fontWeight: "800",
    color: "#f8fafc",
  },
  logoutButton: {
    backgroundColor: "rgba(239, 68, 68, 0.1)",
    padding: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "rgba(239, 68, 68, 0.2)",
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
  statsRow: {
    flexDirection: "row",
    gap: 12,
  },
  statCard: {
    flex: 1,
    backgroundColor: "#1e293b",
    borderRadius: 12,
    padding: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#334155",
    gap: 4,
  },
  statNumber: {
    fontSize: 20,
    fontWeight: "800",
    color: "#f8fafc",
  },
  statLabel: {
    fontSize: 11,
    color: "#94a3b8",
    fontWeight: "600",
  },
  primaryActionCard: {
    backgroundColor: "#2563eb",
    borderRadius: 14,
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
  },
  actionIconContainer: {
    width: 48,
    height: 48,
    borderRadius: 10,
    backgroundColor: "rgba(255, 255, 255, 0.2)",
    alignItems: "center",
    justifyContent: "center",
  },
  actionTextContainer: {
    flex: 1,
  },
  primaryActionTitle: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "700",
  },
  primaryActionSubtitle: {
    color: "#bfdbfe",
    fontSize: 12,
    marginTop: 2,
  },
  secondaryActionCard: {
    backgroundColor: "#1e293b",
    borderRadius: 14,
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    borderWidth: 1,
    borderColor: "#334155",
  },
  historyIconContainer: {
    backgroundColor: "rgba(56, 189, 248, 0.15)",
  },
  secondaryActionTitle: {
    color: "#f8fafc",
    fontSize: 16,
    fontWeight: "700",
  },
  secondaryActionSubtitle: {
    color: "#94a3b8",
    fontSize: 12,
    marginTop: 2,
  },
  sectionHeader: {
    marginTop: 8,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "700",
    color: "#f8fafc",
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
  stopBadge: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#334155",
    alignItems: "center",
    justifyContent: "center",
  },
  stopNumber: {
    color: "#f8fafc",
    fontWeight: "700",
    fontSize: 13,
  },
  stopDetails: {
    flex: 1,
  },
  stopAddress: {
    color: "#f8fafc",
    fontSize: 14,
    fontWeight: "600",
  },
  stopPackage: {
    color: "#94a3b8",
    fontSize: 12,
    marginTop: 2,
  },
  deliverStopButton: {
    backgroundColor: "#16a34a",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 6,
  },
  deliverStopButtonText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 12,
  },
});