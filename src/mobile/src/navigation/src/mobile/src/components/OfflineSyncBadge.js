import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import * as offlineQueueService from "../services/offlineQueueService";

export default function OfflineSyncBadge({
  onSyncComplete,
  pollInterval = 8000,
}) {
  const [pendingCount, setPendingCount] = useState(0);
  const [isSyncing, setIsSyncing] = useState(false);
  const isMountedRef = useRef(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const checkPending = useCallback(async () => {
    try {
      const getCount =
        offlineQueueService?.getPendingQueueCount ||
        offlineQueueService?.default?.getPendingQueueCount;

      if (typeof getCount === "function") {
        const count = await getCount();
        if (isMountedRef.current) {
          setPendingCount(Number(count) || 0);
        }
      }
    } catch (err) {
      console.warn("[OfflineSyncBadge] Error checking pending queue:", err?.message || err);
    }
  }, []);

  useEffect(() => {
    checkPending();
    const interval = setInterval(checkPending, pollInterval);
    return () => clearInterval(interval);
  }, [checkPending, pollInterval]);

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

      if (isMountedRef.current) {
        await checkPending();
      }

      if (typeof onSyncComplete === "function") {
        onSyncComplete(result);
      }

      const synced = result?.syncedCount ?? 0;
      const failed = result?.failedCount ?? 0;

      if (synced > 0 && failed === 0) {
        Alert.alert(
          "Sync Complete",
          `Successfully uploaded ${synced} queued proof${synced > 1 ? "s" : ""}.`
        );
      } else if (synced > 0 && failed > 0) {
        Alert.alert(
          "Partial Sync",
          `Uploaded ${synced} proof(s), but ${failed} remain queued. Server may be partially unreachable.`
        );
      } else if (failed > 0) {
        Alert.alert(
          "Sync Failed",
          "Could not establish connection to the backend. Queued proofs remain stored on this device."
        );
      }
    } catch (err) {
      Alert.alert(
        "Sync Error",
        "An unexpected error occurred during sync. Retrying when connection stabilizes."
      );
    } finally {
      if (isMountedRef.current) {
        setIsSyncing(false);
      }
    }
  };

  if (pendingCount <= 0) {
    return null;
  }

  return (
    <View style={styles.container}>
      <View style={styles.infoGroup}>
        <View style={styles.iconCircle}>
          <MaterialCommunityIcons name="cloud-sync-outline" size={20} color="#f59e0b" />
        </View>
        <View style={styles.textColumn}>
          <View style={styles.titleRow}>
            <Text style={styles.titleText}>Offline Queued</Text>
            <View style={styles.badge}>
              <Text style={styles.badgeText}>{pendingCount}</Text>
            </View>
          </View>
          <Text style={styles.subtitleText}>
            {pendingCount === 1 ? "1 delivery proof" : `${pendingCount} delivery proofs`} awaiting upload
          </Text>
        </View>
      </View>

      <TouchableOpacity
        style={[styles.retryButton, isSyncing && styles.disabledButton]}
        onPress={handleManualSync}
        disabled={isSyncing}
        activeOpacity={0.7}
      >
        {isSyncing ? (
          <ActivityIndicator size="small" color="#0f172a" />
        ) : (
          <>
            <MaterialCommunityIcons name="refresh" size={16} color="#0f172a" />
            <Text style={styles.retryButtonText}>Sync Now</Text>
          </>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
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
    marginVertical: 8,
    elevation: 3,
  },
  infoGroup: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    flex: 1,
  },
  iconCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: "rgba(245, 158, 11, 0.15)",
    alignItems: "center",
    justifyContent: "center",
  },
  textColumn: {
    flex: 1,
  },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  titleText: {
    color: "#f59e0b",
    fontSize: 14,
    fontWeight: "700",
  },
  badge: {
    backgroundColor: "#f59e0b",
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 10,
  },
  badgeText: {
    color: "#0f172a",
    fontSize: 11,
    fontWeight: "800",
  },
  subtitleText: {
    color: "#94a3b8",
    fontSize: 11,
    marginTop: 2,
  },
  retryButton: {
    backgroundColor: "#f59e0b",
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
  },
  disabledButton: {
    opacity: 0.6,
  },
  retryButtonText: {
    color: "#0f172a",
    fontSize: 12,
    fontWeight: "700",
  },
});