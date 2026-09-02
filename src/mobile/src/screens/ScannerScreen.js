import React, { useState } from "react";
import {
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  TextInput,
  Image,
  Alert,
  ActivityIndicator,
  ScrollView,
  Platform,
} from "react-native";
import { MaterialCommunityIcons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import {
  queueDeliveryConfirmation,
  processOfflineQueue,
} from "../services/offlineQueueService";

export default function ScannerScreen({ navigation, route }) {
  const [packageId, setPackageId] = useState(route?.params?.packageId || "pkg-001");
  const [photoUri, setPhotoUri] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Fallback or driver coordinates (Chicago Loop default)
  const defaultCoords = {
    lat: 41.8786,
    lon: -87.6403,
  };

  /**
   * Launch device camera to capture proof of delivery photo
   */
  const handleTakeDeliveryPhoto = async () => {
    try {
      if (Platform.OS !== "web") {
        const { status } = await ImagePicker.requestCameraPermissionsAsync();
        if (status !== "granted") {
          Alert.alert(
            "Permission Required",
            "Camera permission is required to take proof of delivery photos."
          );
          return;
        }
      }

      const result = await ImagePicker.launchCameraAsync({
        allowsEditing: false,
        quality: 0.7, // Compress for faster upload and SQLite payload stability
      });

      if (!result.canceled && result.assets && result.assets.length > 0) {
        setPhotoUri(result.assets[0].uri);
      }
    } catch (err) {
      console.error("[ScannerScreen] Error launching camera:", err);
      Alert.alert("Camera Error", "Could not open camera on this device.");
    }
  };

  /**
   * Remove selected photo
   */
  const handleRemovePhoto = () => {
    setPhotoUri(null);
  };

  /**
   * Confirm and enqueue delivery
   */
  const handleConfirmDelivery = async () => {
    if (!packageId.trim()) {
      Alert.alert("Error", "Please specify a valid Package ID.");
      return;
    }

    setIsSubmitting(true);

    try {
      // 1. Stage delivery into local SQLite database
      const enqueued = await queueDeliveryConfirmation({
        packageId: packageId.trim(),
        driverId: "D001",
        lat: defaultCoords.lat,
        lon: defaultCoords.lon,
        signaturePath: "NATIVE_DRIVER_SIG",
        photoUri: photoUri,
      });

      if (!enqueued) {
        throw new Error("Failed to write to local offline queue.");
      }

      // 2. Proactively trigger a flush if online
      processOfflineQueue().catch((err) =>
        console.warn("[ScannerScreen] Immediate queue drain deferred:", err)
      );

      Alert.alert(
        "Delivery Confirmed",
        `Package ${packageId.trim()} has been logged and queued for synchronization.`,
        [
          {
            text: "OK",
            onPress: () => {
              if (navigation?.canGoBack()) {
                navigation.goBack();
              }
            },
          },
        ]
      );
    } catch (err) {
      console.error("[ScannerScreen] Submission failed:", err);
      Alert.alert("Error", "Could not log delivery. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <MaterialCommunityIcons name="barcode-scan" size={36} color="#3b82f6" />
        <Text style={styles.title}>Confirm Delivery</Text>
        <Text style={styles.subtitle}>
          Verify package details and capture proof of delivery.
        </Text>
      </View>

      {/* Package Identifier Input */}
      <View style={styles.card}>
        <Text style={styles.inputLabel}>PACKAGE IDENTIFIER</Text>
        <TextInput
          style={styles.input}
          value={packageId}
          onChangeText={setPackageId}
          placeholder="e.g. pkg-001"
          placeholderTextColor="#64748b"
          autoCapitalize="none"
          autoCorrect={false}
        />

        {/* Quick select presets */}
        <View style={styles.presetsRow}>
          {["pkg-001", "pkg-002", "pkg-003"].map((id) => (
            <TouchableOpacity
              key={id}
              style={[styles.chip, packageId === id && styles.activeChip]}
              onPress={() => setPackageId(id)}
            >
              <Text
                style={[
                  styles.chipText,
                  packageId === id && styles.activeChipText,
                ]}
              >
                {id}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      {/* Photo Capture Section */}
      <View style={styles.card}>
        <Text style={styles.inputLabel}>PROOF OF DELIVERY PHOTO</Text>

        {photoUri ? (
          <View style={styles.previewContainer}>
            <Image source={{ uri: photoUri }} style={styles.photoPreview} />
            <View style={styles.photoActionRow}>
              <TouchableOpacity
                style={[styles.smallButton, styles.retakeButton]}
                onPress={handleTakeDeliveryPhoto}
              >
                <MaterialCommunityIcons name="camera-retake" size={18} color="#fff" />
                <Text style={styles.buttonTextSmall}>Retake</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.smallButton, styles.deleteButton]}
                onPress={handleRemovePhoto}
              >
                <MaterialCommunityIcons name="trash-can-outline" size={18} color="#fff" />
                <Text style={styles.buttonTextSmall}>Remove</Text>
              </TouchableOpacity>
            </View>
          </View>
        ) : (
          <TouchableOpacity
            style={styles.cameraPlaceholder}
            onPress={handleTakeDeliveryPhoto}
          >
            <MaterialCommunityIcons name="camera-plus-outline" size={44} color="#94a3b8" />
            <Text style={styles.cameraPlaceholderText}>Tap to Capture Photo</Text>
            <Text style={styles.cameraSubtext}>Optional door/porch proof</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Metadata Readout */}
      <View style={styles.infoCard}>
        <View style={styles.infoRow}>
          <MaterialCommunityIcons name="account-outline" size={18} color="#94a3b8" />
          <Text style={styles.infoKey}>Driver ID:</Text>
          <Text style={styles.infoValue}>D001</Text>
        </View>
        <View style={styles.infoRow}>
          <MaterialCommunityIcons name="map-marker-outline" size={18} color="#94a3b8" />
          <Text style={styles.infoKey}>GPS Coords:</Text>
          <Text style={styles.infoValue}>
            {defaultCoords.lat.toFixed(4)}, {defaultCoords.lon.toFixed(4)}
          </Text>
        </View>
        <View style={styles.infoRow}>
          <MaterialCommunityIcons name="draw" size={18} color="#94a3b8" />
          <Text style={styles.infoKey}>Signature:</Text>
          <Text style={styles.infoValue}>Captured (Standard)</Text>
        </View>
      </View>

      {/* Action Buttons */}
      <TouchableOpacity
        style={[styles.submitButton, isSubmitting && styles.disabledButton]}
        onPress={handleConfirmDelivery}
        disabled={isSubmitting}
      >
        {isSubmitting ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <>
            <MaterialCommunityIcons name="check-circle-outline" size={22} color="#fff" />
            <Text style={styles.submitButtonText}>CONFIRM & DELIVER</Text>
          </>
        )}
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    backgroundColor: "#0f172a",
    flexGrow: 1,
  },
  header: {
    alignItems: "center",
    marginBottom: 24,
    marginTop: 10,
  },
  title: {
    fontSize: 22,
    fontWeight: "700",
    color: "#f8fafc",
    marginTop: 8,
  },
  subtitle: {
    fontSize: 13,
    color: "#94a3b8",
    textAlign: "center",
    marginTop: 4,
  },
  card: {
    backgroundColor: "#1e293b",
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: "#334155",
  },
  inputLabel: {
    fontSize: 11,
    fontWeight: "700",
    color: "#94a3b8",
    letterSpacing: 1,
    marginBottom: 8,
  },
  input: {
    backgroundColor: "#0f172a",
    color: "#f8fafc",
    borderWidth: 1,
    borderColor: "#475569",
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 16,
  },
  presetsRow: {
    flexDirection: "row",
    gap: 8,
    marginTop: 12,
  },
  chip: {
    backgroundColor: "#334155",
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
  },
  activeChip: {
    backgroundColor: "#2563eb",
  },
  chipText: {
    color: "#cbd5e1",
    fontSize: 13,
    fontWeight: "500",
  },
  activeChipText: {
    color: "#ffffff",
    fontWeight: "700",
  },
  cameraPlaceholder: {
    borderWidth: 1.5,
    borderStyle: "dashed",
    borderColor: "#475569",
    borderRadius: 10,
    paddingVertical: 24,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#0f172a",
  },
  cameraPlaceholderText: {
    color: "#e2e8f0",
    fontSize: 14,
    fontWeight: "600",
    marginTop: 8,
  },
  cameraSubtext: {
    color: "#64748b",
    fontSize: 12,
    marginTop: 2,
  },
  previewContainer: {
    alignItems: "center",
  },
  photoPreview: {
    width: "100%",
    height: 180,
    borderRadius: 8,
    backgroundColor: "#000",
  },
  photoActionRow: {
    flexDirection: "row",
    gap: 12,
    marginTop: 10,
    width: "100%",
  },
  smallButton: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 6,
    paddingVertical: 8,
    borderRadius: 6,
  },
  retakeButton: {
    backgroundColor: "#3b82f6",
  },
  deleteButton: {
    backgroundColor: "#ef4444",
  },
  buttonTextSmall: {
    color: "#fff",
    fontSize: 13,
    fontWeight: "600",
  },
  infoCard: {
    backgroundColor: "#1e293b",
    borderRadius: 12,
    padding: 16,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: "#334155",
    gap: 8,
  },
  infoRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  infoKey: {
    fontSize: 13,
    color: "#94a3b8",
    width: 90,
  },
  infoValue: {
    fontSize: 13,
    color: "#f8fafc",
    fontWeight: "500",
  },
  submitButton: {
    backgroundColor: "#16a34a",
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    paddingVertical: 14,
    borderRadius: 10,
    marginBottom: 20,
  },
  disabledButton: {
    opacity: 0.6,
  },
  submitButtonText: {
    color: "#ffffff",
    fontSize: 15,
    fontWeight: "700",
    letterSpacing: 0.5,
  },
});