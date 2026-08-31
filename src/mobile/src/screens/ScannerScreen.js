import React, { useState } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  Platform,
} from "react-native";
import client from "../api/client";

export default function ScannerScreen({ navigation }) {
  const [barcodeInput, setBarcodeInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleProcessBarcode = async (scannedCode) => {
    const code = (scannedCode || barcodeInput).trim();
    if (!code) {
      if (Platform.OS === "web") {
        window.alert("Please enter or select a package ID");
      } else {
        Alert.alert("Error", "Please enter or select a package ID");
      }
      return;
    }

    setLoading(true);
    try {
      const msg = `Successfully scanned: ${code}`;
      if (Platform.OS === "web") {
        window.alert(msg);
      } else {
        Alert.alert("Barcode Scanned", msg);
      }

      if (navigation?.goBack) {
        navigation.goBack();
      }
    } catch (err) {
      console.warn("Scan processing error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity
          style={styles.backBtn}
          onPress={() => (navigation?.goBack ? navigation.goBack() : null)}
        >
          <Text style={styles.backText}>← Back to Manifest</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Barcode Scanner</Text>
      </View>

      <View style={styles.content}>
        {/* Scanner Viewfinder Box */}
        <View style={styles.viewfinder}>
          <Text style={styles.viewfinderText}>
            {Platform.OS === "web"
              ? "📷 Camera & Emulated Laser Ready"
              : "Align camera with package barcode"}
          </Text>
          <View style={styles.laserLine} />
        </View>

        {/* Quick Test Barcode Buttons */}
        <Text style={styles.label}>Tap to simulate scan:</Text>
        <View style={styles.quickRow}>
          {["pkg-001", "pkg-002", "pkg-003"].map((id) => (
            <TouchableOpacity
              key={id}
              style={styles.quickBtn}
              onPress={() => handleProcessBarcode(id)}
            >
              <Text style={styles.quickText}>{id}</Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Manual Barcode Input */}
        <TextInput
          style={styles.input}
          placeholder="Or type package ID manually..."
          placeholderTextColor="#94a3b8"
          value={barcodeInput}
          onChangeText={setBarcodeInput}
          autoCapitalize="none"
        />

        <TouchableOpacity
          style={styles.submitBtn}
          onPress={() => handleProcessBarcode()}
          disabled={loading}
        >
          <Text style={styles.submitText}>
            {loading ? "Processing..." : "Submit Scanned Code"}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0f172a" },
  header: {
    paddingTop: 36,
    paddingBottom: 16,
    paddingHorizontal: 20,
    backgroundColor: "#1e293b",
    borderBottomWidth: 1,
    borderBottomColor: "#334155",
  },
  backBtn: { marginBottom: 8 },
  backText: { color: "#38bdf8", fontSize: 14, fontWeight: "600" },
  title: { color: "#fff", fontSize: 20, fontWeight: "700" },
  content: { flex: 1, padding: 24, justifyContent: "center", maxWidth: 500, alignSelf: "center", width: "100%" },
  viewfinder: {
    height: 180,
    borderWidth: 2,
    borderColor: "#38bdf8",
    borderRadius: 16,
    borderStyle: "dashed",
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "rgba(56, 189, 248, 0.04)",
    marginBottom: 24,
    position: "relative",
  },
  viewfinderText: { color: "#94a3b8", fontSize: 13, fontWeight: "500" },
  laserLine: {
    position: "absolute",
    height: 2,
    width: "80%",
    backgroundColor: "#ef4444",
  },
  label: { color: "#cbd5e1", fontSize: 13, marginBottom: 8, fontWeight: "600" },
  quickRow: { flexDirection: "row", gap: 10, marginBottom: 20 },
  quickBtn: {
    flex: 1,
    backgroundColor: "#1e293b",
    paddingVertical: 12,
    borderRadius: 8,
    alignItems: "center",
    borderWidth: 1,
    borderColor: "#334155",
    cursor: "pointer",
  },
  quickText: { color: "#38bdf8", fontWeight: "700", fontSize: 13 },
  input: {
    backgroundColor: "#1e293b",
    color: "#fff",
    borderRadius: 8,
    padding: 14,
    fontSize: 14,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: "#334155",
  },
  submitBtn: {
    backgroundColor: "#2563eb",
    padding: 16,
    borderRadius: 10,
    alignItems: "center",
    cursor: "pointer",
  },
  submitText: { color: "#fff", fontWeight: "700", fontSize: 15 },
});