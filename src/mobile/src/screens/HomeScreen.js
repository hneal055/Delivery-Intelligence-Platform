import React, { useState, useEffect, useCallback } from "react";
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  Platform,
  ScrollView,
  RefreshControl,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import client from "../api/client";

export default function HomeScreen({ navigation }) {
  const [refreshing, setRefreshing] = useState(false);
  const [stats, setStats] = useState({
    assigned: 5,
    completed: 4,
    remaining: 1,
  });
  const [nextStop, setNextStop] = useState({
    stopNumber: 5,
    packageId: "pkg-005",
    address: "222 W Merchandise Mart Plaza",
    tier: "Priority",
  });

  // Pull latest proof count to sync metrics
  const refreshHomeData = useCallback(async () => {
    try {
      const res = await client.get("/delivery/recent-proofs", {
        params: { limit: 50 },
      });
      if (res && Array.isArray(res.data)) {
        const completedCount = res.data.length;
        const totalAssigned = Math.max(5, completedCount);
        const remainingCount = Math.max(0, totalAssigned - completedCount);

        setStats({
          assigned: totalAssigned,
          completed: completedCount,
          remaining: remainingCount,
        });

        if (remainingCount > 0) {
          setNextStop({
            stopNumber: completedCount + 1,
            packageId: `pkg-00${completedCount + 1}`,
            address: "222 W Merchandise Mart Plaza",
            tier: "Priority",
          });
        } else {
          setNextStop(null);
        }
      }
    } catch (_) {
      // Fallback to local state if backend is offline
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    refreshHomeData();
    const unsubscribe = navigation.addListener("focus", () => {
      refreshHomeData();
    });
    return unsubscribe;
  }, [navigation, refreshHomeData]);

  const onRefresh = () => {
    setRefreshing(true);
    refreshHomeData();
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        {/* Top Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.headerPortal}>DRIVER PORTAL</Text>
            <Text style={styles.headerTitle}>Driver D001</Text>
          </View>
          <TouchableOpacity style={styles.logoutButton} activeOpacity={0.7}>
            <MaterialCommunityIcons name="exit-to-app" size={20} color="#f87171" />
          </TouchableOpacity>
        </View>

        <ScrollView
          contentContainerStyle={styles.scrollContent}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#38bdf8" />
          }
        >
          {/* Stat Summary Cards */}
          <View style={styles.statsRow}>
            <View style={styles.statCard}>
              <MaterialCommunityIcons name="truck-delivery-outline" size={22} color="#38bdf8" />
              <Text style={styles.statValue}>{stats.assigned}</Text>
              <Text style={styles.statLabel}>Assigned</Text>
            </View>

            <View style={styles.statCard}>
              <MaterialCommunityIcons name="check-decagram-outline" size={22} color="#4ade80" />
              <Text style={styles.statValue}>{stats.completed}</Text>
              <Text style={styles.statLabel}>Completed</Text>
            </View>

            <View style={styles.statCard}>
              <MaterialCommunityIcons name="clock-outline" size={22} color="#fbbf24" />
              <Text style={styles.statValue}>{stats.remaining}</Text>
              <Text style={styles.statLabel}>Remaining</Text>
            </View>
          </View>

          {/* Quick Action Navigation Cards */}
          <TouchableOpacity
            style={styles.actionCardPrimary}
            onPress={() =>
              navigation.navigate("Scanner", {
                packageId: nextStop ? nextStop.packageId : "",
              })
            }
            activeOpacity={0.8}
          >
            <View style={styles.actionIconBadgePrimary}>
              <MaterialCommunityIcons name="barcode-scan" size={24} color="#ffffff" />
            </View>
            <View style={styles.actionTextGroup}>
              <Text style={styles.actionTitlePrimary}>Scan & Confirm Delivery</Text>
              <Text style={styles.actionSubtitlePrimary}>
                Capture package barcode, photo proof, and signature
              </Text>
            </View>
            <MaterialCommunityIcons name="chevron-right" size={24} color="#ffffff" />
          </TouchableOpacity>

          <TouchableOpacity
            style={styles.actionCardSecondary}
            onPress={() => navigation.navigate("Proofs")}
            activeOpacity={0.8}
          >
            <View style={styles.actionIconBadgeSecondary}>
              <MaterialCommunityIcons name="clipboard-text-outline" size={22} color="#38bdf8" />
            </View>
            <View style={styles.actionTextGroup}>
              <Text style={styles.actionTitleSecondary}>Delivery Proof Log</Text>
              <Text style={styles.actionSubtitleSecondary}>
                Inspect recent delivery photos, timestamps, and coordinates
              </Text>
            </View>
            <MaterialCommunityIcons name="chevron-right" size={22} color="#64748b" />
          </TouchableOpacity>

          {/* Up Next on Route */}
          <View style={styles.upNextSection}>
            <Text style={styles.sectionHeader}>Up Next on Route</Text>

            {nextStop ? (
              <View style={styles.stopCard}>
                <View style={styles.stopNumberBadge}>
                  <Text style={styles.stopNumberText}>{nextStop.stopNumber}</Text>
                </View>

                <View style={styles.stopDetails}>
                  <Text style={styles.stopAddress}>{nextStop.address}</Text>
                  <Text style={styles.stopMeta}>
                    Package: {nextStop.packageId} ({nextStop.tier})
                  </Text>
                </View>

                <TouchableOpacity
                  style={styles.deliverButton}
                  onPress={() =>
                    navigation.navigate("Scanner", { packageId: nextStop.packageId })
                  }
                  activeOpacity={0.7}
                >
                  <Text style={styles.deliverButtonText}>Deliver</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <View style={styles.allDoneBox}>
                <MaterialCommunityIcons name="check-all" size={28} color="#4ade80" />
                <Text style={styles.allDoneText}>All stops completed for today!</Text>
              </View>
            )}
          </View>
        </ScrollView>
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
    paddingTop: Platform.OS === "android" ? (StatusBar.currentHeight || 24) + 10 : 10,
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
  headerPortal: {
    fontSize: 11,
    fontWeight: "800",
    color: "#64748b",
    letterSpacing: 0.8,
  },
  headerTitle: {
    fontSize: 22,
    fontWeight: "800",
    color: "#f8fafc",
    marginTop: 2,
  },
  logoutButton: {
    width: 38,
    height: 38,
    backgroundColor: "rgba(239, 68, 68, 0.12)",
    borderWidth: 1,
    borderColor: "rgba(239, 68, 68, 0.25)",
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
  },
  scrollContent: {
    padding: 16,
    gap: 16,
  },
  statsRow: {
    flexDirection: "row",
    gap: 12,
  },
  statCard: {
    flex: 1,
    backgroundColor: "#1e293b",
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#334155",
    gap: 4,
  },
  statValue: {
    color: "#f8fafc",
    fontSize: 20,
    fontWeight: "800",
  },
  statLabel: {
    color: "#94a3b8",
    fontSize: 11,
    fontWeight: "600",
  },
  actionCardPrimary: {
    backgroundColor: "#2563eb",
    borderRadius: 14,
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
  },
  actionIconBadgePrimary: {
    width: 44,
    height: 44,
    borderRadius: 10,
    backgroundColor: "rgba(255, 255, 255, 0.18)",
    alignItems: "center",
    justifyContent: "center",
  },
  actionTextGroup: {
    flex: 1,
    gap: 2,
  },
  actionTitlePrimary: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "700",
  },
  actionSubtitlePrimary: {
    color: "rgba(255, 255, 255, 0.8)",
    fontSize: 11,
    lineHeight: 15,
  },
  actionCardSecondary: {
    backgroundColor: "#1e293b",
    borderRadius: 14,
    padding: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    borderWidth: 1,
    borderColor: "#334155",
  },
  actionIconBadgeSecondary: {
    width: 44,
    height: 44,
    borderRadius: 10,
    backgroundColor: "rgba(56, 189, 248, 0.12)",
    alignItems: "center",
    justifyContent: "center",
  },
  actionTitleSecondary: {
    color: "#f8fafc",
    fontSize: 15,
    fontWeight: "700",
  },
  actionSubtitleSecondary: {
    color: "#94a3b8",
    fontSize: 11,
    lineHeight: 15,
  },
  upNextSection: {
    gap: 10,
    marginTop: 4,
  },
  sectionHeader: {
    color: "#cbd5e1",
    fontSize: 14,
    fontWeight: "700",
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
  stopNumberBadge: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "#2563eb",
    alignItems: "center",
    justifyContent: "center",
  },
  stopNumberText: {
    color: "#ffffff",
    fontSize: 14,
    fontWeight: "700",
  },
  stopDetails: {
    flex: 1,
    gap: 2,
  },
  stopAddress: {
    color: "#f8fafc",
    fontSize: 13,
    fontWeight: "600",
  },
  stopMeta: {
    color: "#94a3b8",
    fontSize: 11,
  },
  deliverButton: {
    backgroundColor: "#16a34a",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 8,
  },
  deliverButtonText: {
    color: "#ffffff",
    fontSize: 12,
    fontWeight: "700",
  },
  allDoneBox: {
    backgroundColor: "#1e293b",
    borderRadius: 12,
    padding: 18,
    alignItems: "center",
    gap: 8,
    borderWidth: 1,
    borderColor: "rgba(74, 222, 128, 0.3)",
  },
  allDoneText: {
    color: "#4ade80",
    fontSize: 14,
    fontWeight: "700",
  },
});