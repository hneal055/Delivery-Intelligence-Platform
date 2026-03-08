import React, { useEffect, useState } from "react";
import { View, Text, FlatList, StyleSheet, ActivityIndicator, RefreshControl, TouchableOpacity } from "react-native";
import client from "../api/client";
import { useAuthStore } from "../stores/authStore";

export default function HomeScreen() {
  const { driverId, logout } = useAuthStore();
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  const fetchPackages = async () => {
    try {
      setError(null);
      const res = await client.get(`/dispatch/deliveries?driver_id=${driverId}`);
      setPackages(res.data ?? []);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load deliveries");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => { fetchPackages(); }, [driverId]);

  if (loading) return <View style={s.center}><ActivityIndicator size="large" color="#3b5bdb" /></View>;

  return (
    <View style={s.container}>
      <View style={s.header}>
        <Text style={s.heading}>My Deliveries</Text>
        <Text style={s.sub}>{driverId}</Text>
        <TouchableOpacity onPress={logout}><Text style={s.logout}>Sign out</Text></TouchableOpacity>
      </View>

      {error && <Text style={s.error}>{error}</Text>}

      <FlatList
        data={packages}
        keyExtractor={(i) => i.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => { setRefreshing(true); fetchPackages(); }} />}
        renderItem={({ item }) => (
          <View style={s.card}>
            <Text style={s.pkgId}>{item.id}</Text>
            <Text style={s.addr}>{item.dest_address || "No address"}</Text>
            <View style={[s.badge, { backgroundColor: item.status === "delivered" ? "#40c057" : "#3b5bdb" }]}>
              <Text style={s.badgeText}>{item.status}</Text>
            </View>
          </View>
        )}
        ListEmptyComponent={<Text style={s.empty}>No deliveries assigned</Text>}
        contentContainerStyle={{ padding: 16 }}
      />
    </View>
  );
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f5f6fa" },
  center: { flex: 1, justifyContent: "center", alignItems: "center" },
  header: { padding: 20, paddingTop: 56, backgroundColor: "#3b5bdb" },
  heading: { fontSize: 22, fontWeight: "700", color: "#fff" },
  sub: { color: "#b8c9ff", fontSize: 13, marginTop: 2 },
  logout: { color: "#b8c9ff", fontSize: 13, marginTop: 8 },
  error: { color: "#e03131", padding: 16, textAlign: "center" },
  card: { backgroundColor: "#fff", borderRadius: 12, padding: 16, marginBottom: 12,
    shadowColor: "#000", shadowOpacity: 0.06, shadowRadius: 6, elevation: 2 },
  pkgId: { fontWeight: "700", fontSize: 14, color: "#1a1a2e" },
  addr: { color: "#666", fontSize: 13, marginTop: 4 },
  badge: { alignSelf: "flex-start", marginTop: 8, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  badgeText: { color: "#fff", fontSize: 11, fontWeight: "700", textTransform: "uppercase" },
  empty: { textAlign: "center", color: "#aaa", marginTop: 48 },
});
