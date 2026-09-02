import React, { useState, useEffect, useCallback } from "react";
import {
  StyleSheet,
  Text,
  View,
  FlatList,
  Image,
  TouchableOpacity,
  Modal,
  ActivityIndicator,
  RefreshControl,
  SafeAreaView,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import client from "../api/client";

export default function DeliveryHistoryScreen({ navigation }) {
  const [proofs, setProofs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState(null);

  const baseUrl = client?.defaults?.baseURL || "http://localhost:8000";

  const fetchProofs = useCallback(async () => {
    try {
      const response = await fetch(`${baseUrl}/delivery/recent-proofs?limit=50`);
      if (!response.ok) {
        throw new Error(`Failed to fetch proofs: ${response.status}`);
      }
      const data = await response.json();
      setProofs(data);
    } catch (err) {
      console.warn("[DeliveryHistory] Failed to retrieve proofs:", err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [baseUrl]);

  useEffect(() => {
    fetchProofs();
  }, [fetchProofs]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchProofs();
  };

  const renderItem = ({ item }) => {
    const fullPhotoUrl = item.photo_url ? `${baseUrl}${item.photo_url}` : null;
    const formattedDate = item.confirmed_at
      ? new Date(item.confirmed_at).toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
        })
      : "N/A";

    return (
      <View style={styles.card}>
        <View style={styles.cardHeader}>
          <View style={styles.packageTag}>
            <MaterialCommunityIcons name="package-variant-closed" size={16} color="#38bdf8" />
            <Text style={styles.packageIdText}>{item.package_id}</Text>
          </View>
          <View style={styles.statusBadge}>
            <Text style={styles.statusText}>{item.status}</Text>
          </View>
        </View>

        <View style={styles.cardBody}>
          <View style={styles.detailsColumn}>
            <View style={styles.metaRow}>
              <MaterialCommunityIcons name="account-circle-outline" size={15} color="#94a3b8" />
              <Text style={styles.metaLabel}>Driver:</Text>
              <Text style={styles.metaValue}>{item.driver_id}</Text>
            </View>

            <View style={styles.metaRow}>
              <MaterialCommunityIcons name="clock-outline" size={15} color="#94a3b8" />
              <Text style={styles.metaLabel}>Time:</Text>
              <Text style={styles.metaValue}>{formattedDate}</Text>
            </View>

            <View style={styles.metaRow}>
              <MaterialCommunityIcons name="map-marker-outline" size={15} color="#94a3b8" />
              <Text style={styles.metaLabel}>Coords:</Text>
              <Text style={styles.metaValue} numberOfLines={1}>
                {item.dest_lat || "41.8786"}, {item.dest_lon || "-87.6403"}
              </Text>
            </View>

            <View style={styles.metaRow}>
              <MaterialCommunityIcons
                name={item.signature_received ? "draw-pen" : "close-circle-outline"}
                size={15}
                color={item.signature_received ? "#4ade80" : "#64748b"}
              />
              <Text style={styles.metaLabel}>Signature:</Text>
              <Text style={[styles.metaValue, item.signature_received && styles.signatureText]}>
                {item.signature_received ? "Captured" : "None"}
              </Text>
            </View>
          </View>

          {/* Thumbnail preview button */}
          <TouchableOpacity
            style={styles.thumbnailContainer}
            disabled={!fullPhotoUrl}
            onPress={() => fullPhotoUrl && setSelectedPhoto(fullPhotoUrl)}
          >
            {fullPhotoUrl ? (
              <>
                <Image source={{ uri: fullPhotoUrl }} style={styles.thumbnail} />
                <View style={styles.expandIconBadge}>
                  <MaterialCommunityIcons name="arrow-expand" size={12} color="#ffffff" />
                </View>
              </>
            ) : (
              <View style={styles.noPhotoPlaceholder}>
                <MaterialCommunityIcons name="camera-off-outline" size={24} color="#64748b" />
                <Text style={styles.noPhotoText}>No Photo</Text>
              </View>
            )}
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.container}>
      {/* Top Bar */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Delivery Proof Log</Text>
        <TouchableOpacity style={styles.refreshIconButton} onPress={onRefresh}>
          <MaterialCommunityIcons name="refresh" size={22} color="#38bdf8" />
        </TouchableOpacity>
      </View>

      {/* Main List */}
      {loading ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color="#38bdf8" />
          <Text style={styles.loadingText}>Loading delivery proofs...</Text>
        </View>
      ) : (
        <FlatList
          data={proofs}
          keyExtractor={(item) => String(item.id || item.package_id + item.confirmed_at)}
          renderItem={renderItem}
          contentContainerStyle={styles.listContent}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#38bdf8" />
          }
          ListEmptyComponent={
            <View style={styles.centerContainer}>
              <MaterialCommunityIcons name="cube-outline" size={48} color="#475569" />
              <Text style={styles.emptyTitle}>No Proofs Logged</Text>
              <Text style={styles.emptySubtitle}>
                Completed deliveries with signature or photo documentation will appear here.
              </Text>
            </View>
          }
        />
      )}

      {/* High-Resolution Photo Viewer Modal */}
      <Modal visible={Boolean(selectedPhoto)} transparent={true} animationType="fade">
        <View style={styles.modalOverlay}>
          <SafeAreaView style={styles.modalContent}>
            <TouchableOpacity
              style={styles.closeButton}
              onPress={() => setSelectedPhoto(null)}
            >
              <MaterialCommunityIcons name="close" size={24} color="#ffffff" />
            </TouchableOpacity>

            {selectedPhoto && (
              <Image
                source={{ uri: selectedPhoto }}
                style={styles.fullImage}
                resizeMode="contain"
              />
            )}
          </SafeAreaView>
        </View>
      </Modal>
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
    fontSize: 18,
    fontWeight: "700",
    color: "#f8fafc",
  },
  refreshIconButton: {
    padding: 6,
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
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
    paddingBottom: 8,
    borderBottomWidth: 1,
    borderBottomColor: "#334155",
  },
  packageTag: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  packageIdText: {
    fontSize: 15,
    fontWeight: "700",
    color: "#f8fafc",
  },
  statusBadge: {
    backgroundColor: "rgba(34, 197, 94, 0.15)",
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: "rgba(34, 197, 94, 0.3)",
  },
  statusText: {
    color: "#4ade80",
    fontSize: 11,
    fontWeight: "700",
    letterSpacing: 0.5,
  },
  cardBody: {
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 12,
  },
  detailsColumn: {
    flex: 1,
    gap: 5,
    justifyContent: "center",
  },
  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  metaLabel: {
    fontSize: 12,
    color: "#94a3b8",
    width: 60,
  },
  metaValue: {
    fontSize: 12,
    color: "#cbd5e1",
    fontWeight: "500",
  },
  signatureText: {
    color: "#4ade80",
  },
  thumbnailContainer: {
    width: 84,
    height: 84,
    borderRadius: 8,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: "#475569",
    position: "relative",
  },
  thumbnail: {
    width: "100%",
    height: "100%",
  },
  expandIconBadge: {
    position: "absolute",
    bottom: 4,
    right: 4,
    backgroundColor: "rgba(15, 23, 42, 0.8)",
    padding: 3,
    borderRadius: 4,
  },
  noPhotoPlaceholder: {
    width: "100%",
    height: "100%",
    backgroundColor: "#0f172a",
    alignItems: "center",
    justifyContent: "center",
  },
  noPhotoText: {
    fontSize: 10,
    color: "#64748b",
    marginTop: 3,
    fontWeight: "500",
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
  modalOverlay: {
    flex: 1,
    backgroundColor: "rgba(0, 0, 0, 0.95)",
    justifyContent: "center",
    alignItems: "center",
  },
  modalContent: {
    flex: 1,
    width: "100%",
    justifyContent: "center",
    alignItems: "center",
  },
  closeButton: {
    position: "absolute",
    top: 40,
    right: 20,
    zIndex: 10,
    backgroundColor: "#1e293b",
    padding: 10,
    borderRadius: 25,
  },
  fullImage: {
    width: "95%",
    height: "80%",
    borderRadius: 8,
  },
});