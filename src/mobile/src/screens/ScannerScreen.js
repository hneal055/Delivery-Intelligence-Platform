import React, { useState, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  TextInput,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as Haptics from "expo-haptics";
import { queueDeliveryConfirmation } from "../services/offlineQueueService";
import { useAuthStore } from "../stores/authStore";

export default function ScannerScreen({ navigation }) {
  const [permission, requestPermission] = useCameraPermissions();
  const [scanned, setScanned] = useState(false);
  const [manualInput, setManualInput] = useState("");
  const [detectedPackage, setDetectedPackage] = useState(null);
  const [confirmModalVisible, setConfirmModalVisible] = useState(false);

  const user = useAuthStore((s) => s.user);

  const getDriverId = () => {
    if (typeof user === "string") {
      const match = user.match(/\d+/);
      return match ? `D${match[0].padStart(3, "0")}` : user;
    }
    if (user?.driver_id) return user.driver_id;
    if (user?.username) {
      const match = user.username.match(/\d+/);
      return match ? `D${match[0].padStart(3, "0")}` : user.username;
    }
    return "D001";
  };

  const driverId = getDriverId();

  const handleBarcodeScanned = ({ data }) => {
    if (scanned || confirmModalVisible) return;
    setScanned(true);

    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    promptDeliveryConfirmation(data.trim());
  };

  const promptDeliveryConfirmation = (pkgId) => {
    setDetectedPackage(pkgId);
    setConfirmModalVisible(true);
  };

  const handleConfirmAndDeliver = async () => {
    const pkgId = detectedPackage;
    if (!pkgId) return;

    try {
      // 1. Log to local SQLite offline queue
      await queueDeliveryConfirmation({
        packageId: pkgId,
        driverId: driverId,
        lat: 41.8786,
        lon: -87.6403,
        signaturePath: "SCANNED_VIA_CAMERA",
      });

      setConfirmModalVisible(false);

      // 2. Notify driver and pass deliveredPackageId back to HomeScreen
      Alert.alert("Notice", `Delivery logged locally for ${pkgId}.`, [
        {
          text: "OK",
          onPress: () => {
            navigation.navigate("Home", { deliveredPackageId: pkgId });
          },
        },
      ]);
    } catch (err) {
      console.warn("Failed to log delivery locally:", err);
      Alert.alert("Error", "Could not log delivery to local storage.");
      setScanned(false);
      setConfirmModalVisible(false);
    }
  };

  const handleManualSubmit = () => {
    if (!manualInput.trim()) return;
    const pkgId = manualInput.trim();
    setManualInput("");
    promptDeliveryConfirmation(pkgId);
  };

  return (
    <SafeAreaView style={s.container}>
      {/* Top Header */}
      <View style={s.header}>
        <TouchableOpacity
          style={s.backBtn}
          onPress={() => navigation.navigate("Home")}
        >
          <Text style={s.backBtnText}>← Back to Manifest</Text>
        </TouchableOpacity>
        <Text style={s.headerTitle}>Scan & Confirm Delivery</Text>
      </View>

      <KeyboardAvoidingView
        style={s.content}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        {/* Camera Viewfinder Viewport */}
        <View style={s.cameraCard}>
          {!permission?.granted ? (
            <View style={s.permissionBox}>
              <Text style={s.permissionText}>Camera permission is required.</Text>
              <TouchableOpacity style={s.grantBtn} onPress={requestPermission}>
                <Text style={s.grantBtnText}>Grant Permission</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <View style={s.cameraWrapper}>
              <CameraView
                style={StyleSheet.absoluteFillObject}
                facing="back"
                barcodeScannerSettings={{
                  barcodeTypes: ["qr", "code128", "code39", "ean13", "upc_a"],
                }}
                onBarcodeScanned={scanned ? undefined : handleBarcodeScanned}
              />
              <View style={s.targetBox} />
            </View>
          )}
        </View>

        {/* Quick Simulation Buttons */}
        <View style={s.simSection}>
          <Text style={s.sectionLabel}>Simulate Package Scan:</Text>
          <View style={s.simBtnRow}>
            {["pkg-001", "pkg-002", "pkg-003"].map((id) => (
              <TouchableOpacity
                key={id}
                style={s.simChip}
                onPress={() => promptDeliveryConfirmation(id)}
              >
                <Text style={s.simChipText}>{id}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Manual Barcode / ADB Input */}
        <View style={s.manualSection}>
          <TextInput
            style={s.textInput}
            placeholder="Or enter package ID manually..."
            placeholderTextColor="#64748b"
            value={manualInput}
            onChangeText={setManualInput}
            autoCapitalize="none"
          />
          <TouchableOpacity
            style={s.confirmInputBtn}
            onPress={handleManualSubmit}
          >
            <Text style={s.confirmInputBtnText}>Confirm Entered Package</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>

      {/* Confirmation Overlay Dialog */}
      {confirmModalVisible && (
        <View style={s.modalBackdrop}>
          <View style={s.dialogBox}>
            <Text style={s.dialogTitle}>Confirm Delivery</Text>
            <Text style={s.dialogSubtitle}>
              Scanned package: <Text style={s.boldText}>{detectedPackage}</Text>
            </Text>
            <Text style={s.dialogDesc}>
              Do you want to confirm delivery and upload proof for Driver {driverId}?
            </Text>

            <View style={s.dialogActions}>
              <TouchableOpacity
                style={s.cancelBtn}
                onPress={() => {
                  setConfirmModalVisible(false);
                  setScanned(false);
                }}
              >
                <Text style={s.cancelBtnText}>CANCEL</Text>
              </TouchableOpacity>

              <TouchableOpacity
                style={s.deliverBtn}
                onPress={handleConfirmAndDeliver}
              >
                <Text style={s.deliverBtnText}>CONFIRM & DELIVER</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0b1120",
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#1e293b",
  },
  backBtn: {
    paddingBottom: 6,
  },
  backBtnText: {
    color: "#38bdf8",
    fontSize: 14,
    fontWeight: "600",
  },
  headerTitle: {
    color: "#f8fafc",
    fontSize: 20,
    fontWeight: "800",
  },
  content: {
    flex: 1,
    padding: 20,
    justifyContent: "space-around",
  },
  cameraCard: {
    height: 280,
    borderRadius: 16,
    overflow: "hidden",
    backgroundColor: "#020617",
    borderWidth: 1,
    borderColor: "#1e293b",
  },
  cameraWrapper: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  targetBox: {
    width: 220,
    height: 140,
    borderWidth: 2,
    borderColor: "#38bdf8",
    borderRadius: 12,
    backgroundColor: "transparent",
  },
  permissionBox: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 20,
  },
  permissionText: {
    color: "#94a3b8",
    fontSize: 14,
    marginBottom: 12,
    textAlign: "center",
  },
  grantBtn: {
    backgroundColor: "#2563eb",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 8,
  },
  grantBtnText: {
    color: "#fff",
    fontWeight: "700",
  },
  simSection: {
    marginVertical: 10,
  },
  sectionLabel: {
    color: "#94a3b8",
    fontSize: 12,
    fontWeight: "600",
    marginBottom: 8,
    textTransform: "uppercase",
  },
  simBtnRow: {
    flexDirection: "row",
    gap: 10,
  },
  simChip: {
    flex: 1,
    backgroundColor: "#1e293b",
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#334155",
  },
  simChipText: {
    color: "#38bdf8",
    fontWeight: "700",
    fontSize: 13,
  },
  manualSection: {
    marginTop: 10,
  },
  textInput: {
    backgroundColor: "#0f172a",
    borderWidth: 1,
    borderColor: "#334155",
    color: "#f8fafc",
    borderRadius: 10,
    paddingHorizontal: 16,
    paddingVertical: 12,
    fontSize: 14,
    marginBottom: 12,
  },
  confirmInputBtn: {
    backgroundColor: "#1e3a8a",
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: "center",
  },
  confirmInputBtnText: {
    color: "#93c5fd",
    fontWeight: "700",
    fontSize: 14,
  },
  modalBackdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0, 0, 0, 0.75)",
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  dialogBox: {
    width: "100%",
    backgroundColor: "#334155",
    borderRadius: 12,
    padding: 20,
    elevation: 10,
  },
  dialogTitle: {
    fontSize: 18,
    fontWeight: "800",
    color: "#f8fafc",
    marginBottom: 8,
  },
  dialogSubtitle: {
    fontSize: 14,
    color: "#cbd5e1",
    marginBottom: 10,
  },
  boldText: {
    color: "#fff",
    fontWeight: "700",
  },
  dialogDesc: {
    fontSize: 13,
    color: "#94a3b8",
    lineHeight: 18,
    marginBottom: 20,
  },
  dialogActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: 16,
  },
  cancelBtn: {
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  cancelBtnText: {
    color: "#94a3b8",
    fontWeight: "700",
    fontSize: 13,
  },
  deliverBtn: {
    paddingVertical: 8,
    paddingHorizontal: 12,
  },
  deliverBtnText: {
    color: "#34d399",
    fontWeight: "800",
    fontSize: 13,
  },
});