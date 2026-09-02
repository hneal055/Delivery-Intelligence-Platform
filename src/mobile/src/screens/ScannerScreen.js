import React, { useState, useEffect } from "react";
import {
  StyleSheet,
  Text,
  View,
  TextInput,
  TouchableOpacity,
  SafeAreaView,
  StatusBar,
  Platform,
  Alert,
  ActivityIndicator,
  Image,
  ScrollView,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import client from "../api/client";
import * as offlineQueueService from "../services/offlineQueueService";

export default function ScannerScreen({ route, navigation }) {
  const [packageId, setPackageId] = useState(route?.params?.packageId || "");
  const [driverId] = useState("D001");
  const [photoUri, setPhotoUri] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Sync packageId whenever route params change
  useEffect(() => {
    if (route?.params?.packageId) {
      setPackageId(route.params.packageId);
    }
  }, [route?.params?.packageId]);

  // Re-sync packageId whenever screen gains focus from Manifest or deep link
  useEffect(() => {
    const unsubscribe = navigation.addListener("focus", () => {
      if (route?.params?.packageId) {
        setPackageId(route.params.packageId);
      }
    });
    return unsubscribe;
  }, [navigation, route?.params?.packageId]);

  // Request camera permissions on mount
  useEffect(() => {
    (async () => {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== "granted") {
        console.warn("[ScannerScreen] Camera permission not granted");
      }
    })();
  }, []);

  const handleTakePhoto = async () => {
    try {
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: false,
        quality: 0.6,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        setPhotoUri(result.assets[0].uri);
      }
    } catch (err) {
      console.warn("[ScannerScreen] Camera fallback for emulator:", err.message);
      setPhotoUri("https://via.placeholder.com/600x400.png?text=Proof+Photo+Mock");
    }
  };

  const handlePickFromGallery = async () => {
    try {
      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: false,
        quality: 0.6,
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        setPhotoUri(result.assets[0].uri);
      }
    } catch (err) {
      Alert.alert("Gallery Error", err.message);
    }
  };

  const handleClearPackageId = () => {
    setPackageId("");
    if (navigation.setParams) {
      navigation.setParams({ packageId: "" });
    }
  };

  const handleConfirmDelivery = async () => {
    // Check input state first; fall back to route parameter
    const cleanPackageId = (packageId || route?.params?.packageId || "").trim();

    if (!cleanPackageId) {
      Alert.alert(
        "Missing Package ID",
        "Please scan or enter a Package ID before confirming delivery."
      );
      return;
    }

    setIsSubmitting(true);

    const deliveryPayload = {
      package_id: cleanPackageId,
      driver_id: driverId,
      dest_lat: 41.8819,
      dest_lon: -87.6398,
      status: "DELIVERED",
      photo_uri: photoUri,
    };

    try {
      const formData = new FormData();
      formData.append("package_id", deliveryPayload.package_id);
      formData.append("driver_id", deliveryPayload.driver_id);
      formData.append("dest_lat", String(deliveryPayload.dest_lat));
      formData.append("dest_lon", String(deliveryPayload.dest_lon));
      formData.append("status", deliveryPayload.status);

      if (photoUri && !photoUri.startsWith("http")) {
        const filename = photoUri.split("/").pop() || "proof.jpg";
        const match = /\.(\w+)$/.exec(filename);
        const type = match ? `image/${match[1]}` : "image/jpeg";
        formData.append("photo", {
          uri: photoUri,
          name: filename,
          type,
        });
      }

      const res = await client.post("/delivery/confirm", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        timeout: 8000,
      });

      if (res.status === 200 || res.status === 201) {
        Alert.alert(
          "Delivery Confirmed",
          `Proof of delivery successfully verified for ${cleanPackageId}.`,
          [
            {
              text: "Back to Manifest",
              onPress: () => {
                handleClearPackageId();
                setPhotoUri(null);
                navigation.navigate("ManifestTab");
              },
            },
            {
              text: "Scan Next",
              onPress: () => {
                handleClearPackageId();
                setPhotoUri(null);
              },
            },
          ]
        );
      } else {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
    } catch (err) {
      console.warn("[ScannerScreen] Network delivery failed, queuing offline:", err?.message || err);

      try {
        const queueDelivery =
          offlineQueueService?.queueOfflineDelivery ||
          offlineQueueService?.default?.queueOfflineDelivery;

        if (typeof queueDelivery === "function") {
          await queueDelivery(deliveryPayload);

          Alert.alert(
            "Saved Offline",
            `Network unavailable. Delivery for ${cleanPackageId} saved locally to offline queue.`,
            [
              {
                text: "Back to Manifest",
                onPress: () => {
                  handleClearPackageId();
                  setPhotoUri(null);
                  navigation.navigate("ManifestTab");
                },
              },
              {
                text: "OK",
                onPress: () => {
                  handleClearPackageId();
                  setPhotoUri(null);
                },
              },
            ]
          );
        } else {
          Alert.alert("Sync Notice", "Unable to reach server. Please retry.");
        }
      } catch (queueErr) {
        Alert.alert("Storage Error", "Could not queue delivery record locally.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const activePackageDisplay = packageId || route?.params?.packageId || "";

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.headerTitle}>Delivery Scanner</Text>
            <Text style={styles.headerSubtitle}>
              Driver {driverId} • Proof Verification
            </Text>
          </View>
          {activePackageDisplay ? (
            <View style={styles.linkedBadge}>
              <MaterialCommunityIcons name="link-variant" size={14} color="#38bdf8" />
              <Text style={styles.linkedBadgeText}>Manifest Stop</Text>
            </View>
          ) : null}
        </View>

        <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
          {/* Target Package Input */}
          <View style={styles.sectionCard}>
            <Text style={styles.sectionLabel}>TARGET PACKAGE</Text>
            <View style={styles.inputContainer}>
              <MaterialCommunityIcons name="barcode-scan" size={22} color="#38bdf8" />
              <TextInput
                style={styles.textInput}
                placeholder="Scan or enter Package ID (e.g. pkg-004)"
                placeholderTextColor="#64748b"
                value={packageId}
                onChangeText={setPackageId}
                autoCapitalize="characters"
                autoCorrect={false}
              />
              {activePackageDisplay.length > 0 && (
                <TouchableOpacity
                  onPress={handleClearPackageId}
                  hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
                >
                  <MaterialCommunityIcons name="close-circle" size={20} color="#94a3b8" />
                </TouchableOpacity>
              )}
            </View>
          </View>

          {/* Photo Capture Section */}
          <View style={styles.sectionCard}>
            <Text style={styles.sectionLabel}>PROOF OF DELIVERY PHOTO</Text>

            {photoUri ? (
              <View style={styles.previewContainer}>
                <Image source={{ uri: photoUri }} style={styles.photoPreview} />
                <TouchableOpacity
                  style={styles.removePhotoButton}
                  onPress={() => setPhotoUri(null)}
                >
                  <MaterialCommunityIcons name="trash-can-outline" size={18} color="#f87171" />
                  <Text style={styles.removePhotoText}>Retake Photo</Text>
                </TouchableOpacity>
              </View>
            ) : (
              <View style={styles.photoActionRow}>
                <TouchableOpacity
                  style={styles.cameraButton}
                  onPress={handleTakePhoto}
                  activeOpacity={0.7}
                >
                  <MaterialCommunityIcons name="camera" size={24} color="#ffffff" />
                  <Text style={styles.cameraButtonText}>Take Photo</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={styles.galleryButton}
                  onPress={handlePickFromGallery}
                  activeOpacity={0.7}
                >
                  <MaterialCommunityIcons name="image-multiple-outline" size={22} color="#38bdf8" />
                  <Text style={styles.galleryButtonText}>Choose</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>

          {/* Metadata Section */}
          <View style={styles.metaCard}>
            <View style={styles.metaRow}>
              <MaterialCommunityIcons name="crosshairs-gps" size={16} color="#94a3b8" />
              <Text style={styles.metaText}>Coordinates: 41.8819, -87.6398 (Chicago, IL)</Text>
            </View>
            <View style={styles.metaRow}>
              <MaterialCommunityIcons name="shield-check-outline" size={16} color="#94a3b8" />
              <Text style={styles.metaText}>Verification: Instant Server Upload / Offline Fallback</Text>
            </View>
          </View>

          {/* Confirm Delivery Button */}
          <TouchableOpacity
            style={[styles.confirmButton, isSubmitting && styles.disabledButton]}
            onPress={handleConfirmDelivery}
            disabled={isSubmitting}
            activeOpacity={0.8}
          >
            {isSubmitting ? (
              <ActivityIndicator size="small" color="#ffffff" />
            ) : (
              <>
                <MaterialCommunityIcons name="check-circle-outline" size={22} color="#ffffff" />
                <Text style={styles.confirmButtonText}>Confirm Delivery</Text>
              </>
            )}
          </TouchableOpacity>
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
  linkedBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    backgroundColor: "rgba(56, 189, 248, 0.15)",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: "rgba(56, 189, 248, 0.3)",
  },
  linkedBadgeText: {
    color: "#38bdf8",
    fontSize: 11,
    fontWeight: "700",
  },
  scrollContent: {
    padding: 16,
    gap: 16,
  },
  sectionCard: {
    backgroundColor: "#1e293b",
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: "#334155",
    gap: 10,
  },
  sectionLabel: {
    fontSize: 11,
    fontWeight: "800",
    color: "#94a3b8",
    letterSpacing: 0.5,
  },
  inputContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#0f172a",
    borderWidth: 1,
    borderColor: "#334155",
    borderRadius: 8,
    paddingHorizontal: 12,
    height: 48,
    gap: 10,
  },
  textInput: {
    flex: 1,
    color: "#f8fafc",
    fontSize: 15,
    fontWeight: "600",
  },
  photoActionRow: {
    flexDirection: "row",
    gap: 10,
  },
  cameraButton: {
    flex: 1,
    backgroundColor: "#2563eb",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 14,
    borderRadius: 8,
  },
  cameraButtonText: {
    color: "#ffffff",
    fontWeight: "700",
    fontSize: 14,
  },
  galleryButton: {
    backgroundColor: "rgba(56, 189, 248, 0.1)",
    borderWidth: 1,
    borderColor: "rgba(56, 189, 248, 0.3)",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingHorizontal: 16,
    borderRadius: 8,
  },
  galleryButtonText: {
    color: "#38bdf8",
    fontWeight: "700",
    fontSize: 13,
  },
  previewContainer: {
    alignItems: "center",
    gap: 10,
  },
  photoPreview: {
    width: "100%",
    height: 180,
    borderRadius: 8,
    backgroundColor: "#0f172a",
  },
  removePhotoButton: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingVertical: 4,
  },
  removePhotoText: {
    color: "#f87171",
    fontSize: 13,
    fontWeight: "600",
  },
  metaCard: {
    backgroundColor: "#0f172a",
    borderRadius: 8,
    padding: 12,
    gap: 8,
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  metaText: {
    color: "#64748b",
    fontSize: 11,
  },
  confirmButton: {
    backgroundColor: "#16a34a",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 15,
    borderRadius: 10,
    marginTop: 8,
  },
  confirmButtonText: {
    color: "#ffffff",
    fontSize: 16,
    fontWeight: "800",
  },
  disabledButton: {
    opacity: 0.6,
  },
});