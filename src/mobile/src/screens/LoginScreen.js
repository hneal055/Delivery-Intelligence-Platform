import React, { useState } from "react";
import { View, Text, TextInput, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, Platform } from "react-native";
import { useAuthStore } from "../stores/authStore";

const QUICK_FILL = [
  { label: "Admin",       username: "admin",       password: "adminpassword" },
  { label: "Dispatcher",  username: "dispatcher1", password: "dispatcherpassword" },
  { label: "Driver 1",    username: "driver1",     password: "driverpassword" },
];

export default function LoginScreen() {
  const login = useAuthStore((s) => s.login);
  const logout = useAuthStore((s) => s.logout);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const showAlert = (title, message) => {
    if (Platform.OS === "web") {
      window.alert(`${title}: ${message}`);
    } else {
      Alert.alert(title, message);
    }
  };

  const handleLogin = async () => {
    if (!username || !password) {
      showAlert("Error", "Enter username and password");
      return;
    }
    setLoading(true);
    try {
      await login(username.trim(), password);
    } catch (err) {
      showAlert("Login Failed", err.response?.data?.detail || "Check credentials and try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleResetCache = async () => {
    try {
      if (typeof logout === "function") {
        await logout();
      }
      if (Platform.OS === "web" && typeof window !== "undefined" && window.localStorage) {
        window.localStorage.clear();
      }
      showAlert("Cache Cleared", "Local app session cleared.");
    } catch (_) {}
  };

  return (
    <View style={s.container}>
      <Text style={s.title}>Driver App</Text>
      <Text style={s.subtitle}>Delivery Intelligence Platform</Text>

      <TextInput
        style={s.input}
        placeholder="Username"
        autoCapitalize="none"
        value={username}
        onChangeText={setUsername}
      />
      <TextInput
        style={s.input}
        placeholder="Password"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      <TouchableOpacity style={s.btn} onPress={handleLogin} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={s.btnText}>Sign In</Text>}
      </TouchableOpacity>

      <Text style={s.hint}>Quick fill:</Text>
      <View style={s.row}>
        {QUICK_FILL.map((c) => (
          <TouchableOpacity
            key={c.label}
            style={s.chip}
            onPress={() => {
              setUsername(c.username);
              setPassword(c.password);
            }}
          >
            <Text style={s.chipText}>{c.label}</Text>
          </TouchableOpacity>
        ))}
      </View>

      <TouchableOpacity style={s.clearBtn} onPress={handleResetCache}>
        <Text style={s.clearBtnText}>Reset / Clear App Cache</Text>
      </TouchableOpacity>
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 28, backgroundColor: "#f5f6fa" },
  title: { fontSize: 28, fontWeight: "700", textAlign: "center", marginBottom: 4, color: "#1a1a2e" },
  subtitle: { fontSize: 13, textAlign: "center", marginBottom: 32, color: "#888" },
  input: {
    backgroundColor: "#fff",
    borderRadius: 10,
    padding: 14,
    marginBottom: 14,
    borderWidth: 1,
    borderColor: "#dde",
    fontSize: 15,
  },
  btn: {
    backgroundColor: "#3b5bdb",
    borderRadius: 10,
    padding: 16,
    alignItems: "center",
    marginTop: 4,
  },
  btnText: { color: "#fff", fontWeight: "700", fontSize: 16 },
  hint: { color: "#aaa", fontSize: 12, marginTop: 24, marginBottom: 8, textAlign: "center" },
  row: { flexDirection: "row", justifyContent: "center", gap: 8 },
  chip: { backgroundColor: "#e3e8ff", paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20 },
  chipText: { color: "#3b5bdb", fontSize: 13, fontWeight: "600" },
  clearBtn: { marginTop: 32, alignItems: "center", padding: 10 },
  clearBtnText: { color: "#e03131", fontSize: 13, fontWeight: "600", textDecorationLine: "underline" },
});