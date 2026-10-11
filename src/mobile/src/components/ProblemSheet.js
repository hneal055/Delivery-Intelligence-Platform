import React, { useState } from "react";
import {
  Modal,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  StyleSheet,
} from "react-native";
import { reportProblem } from "../api/client";

const REASONS = [
  "Recipient not available / business closed",
  "Refused by recipient",
  "Wrong or incomplete address",
  "Could not access building or dock",
  "Package not ready at pickup",
  "Package damaged",
  "Other",
];

/**
 * "Report problem" for a stop the driver cannot complete. Dispatch sees the
 * reason immediately and can send the package back out (Reopen).
 */
export default function ProblemSheet({ visible, packageId, driverId, onClose, onReported }) {
  const [reason, setReason] = useState(null);
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);

  const reset = () => {
    setReason(null);
    setNote("");
  };

  const submit = async () => {
    const text = [reason, note.trim()].filter(Boolean).join(": ");
    setSending(true);
    try {
      await reportProblem(packageId, driverId, text);
      reset();
      onReported?.();
      Alert.alert("Problem reported", "Dispatch has been told and will follow up.");
    } catch (err) {
      const detail = err.response?.data?.detail;
      Alert.alert(
        "Could not report",
        typeof detail === "string" ? detail : "Check your connection and try again."
      );
    } finally {
      setSending(false);
    }
  };

  const needsNote = reason === "Other" && note.trim().length < 2;

  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <Text style={styles.title}>Report a problem</Text>
          <Text style={styles.subtitle}>{packageId}</Text>

          {REASONS.map((r) => (
            <TouchableOpacity
              key={r}
              style={[styles.reason, reason === r && styles.reasonSelected]}
              onPress={() => setReason(r)}
            >
              <Text style={[styles.reasonText, reason === r && styles.reasonTextSelected]}>{r}</Text>
            </TouchableOpacity>
          ))}

          <TextInput
            style={styles.note}
            placeholder={reason === "Other" ? "Describe the problem (required)" : "Add a note (optional)"}
            placeholderTextColor="#64748b"
            value={note}
            onChangeText={setNote}
            multiline
          />

          <View style={styles.actions}>
            <TouchableOpacity
              style={styles.cancel}
              onPress={() => {
                reset();
                onClose();
              }}
              disabled={sending}
            >
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.send, (!reason || needsNote || sending) && styles.disabled]}
              onPress={submit}
              disabled={!reason || needsNote || sending}
            >
              {sending ? <ActivityIndicator color="#fff" /> : <Text style={styles.sendText}>Send to dispatch</Text>}
            </TouchableOpacity>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: { flex: 1, backgroundColor: "rgba(0,0,0,0.6)", justifyContent: "flex-end" },
  sheet: { backgroundColor: "#0f172a", padding: 20, borderTopLeftRadius: 16, borderTopRightRadius: 16 },
  title: { color: "#f8fafc", fontSize: 18, fontWeight: "700" },
  subtitle: { color: "#94a3b8", fontSize: 12, marginBottom: 12 },
  reason: { padding: 12, borderRadius: 8, borderWidth: 1, borderColor: "#334155", marginBottom: 8 },
  reasonSelected: { borderColor: "#f87171", backgroundColor: "#450a0a" },
  reasonText: { color: "#cbd5e1", fontSize: 14 },
  reasonTextSelected: { color: "#fecaca", fontWeight: "600" },
  note: {
    borderWidth: 1, borderColor: "#334155", borderRadius: 8, color: "#f8fafc",
    padding: 10, minHeight: 60, marginTop: 4, marginBottom: 12,
  },
  actions: { flexDirection: "row", justifyContent: "flex-end", gap: 12 },
  cancel: { paddingVertical: 12, paddingHorizontal: 16 },
  cancelText: { color: "#94a3b8", fontSize: 15 },
  send: { backgroundColor: "#dc2626", paddingVertical: 12, paddingHorizontal: 18, borderRadius: 8 },
  sendText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  disabled: { opacity: 0.5 },
});
