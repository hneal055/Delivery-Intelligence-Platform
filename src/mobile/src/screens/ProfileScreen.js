import React from 'react';
import { View, Text, Button, StyleSheet } from 'react-native';
import { useAuthStore } from '../stores/authStore';
import { useLocationStore } from '../stores/locationStore';

export default function ProfileScreen() {
  const driverId = useAuthStore((s) => s.driverId);
  const logout = useAuthStore((s) => s.logout);
  const location = useLocationStore((s) => s.location);
  const errorMsg = useLocationStore((s) => s.errorMsg);

  return (
    <View style={styles.container}>
      <View style={styles.card}>
        <Text style={styles.title}>Driver Profile</Text>
        <Text style={styles.label}>Driver ID</Text>
        <Text style={styles.value}>{driverId}</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.title}>GPS Status</Text>
        {errorMsg ? (
          <Text style={styles.error}>{errorMsg}</Text>
        ) : location ? (
          <>
            <Text style={styles.label}>Latitude</Text>
            <Text style={styles.value}>{location.coords.latitude.toFixed(6)}</Text>
            <Text style={styles.label}>Longitude</Text>
            <Text style={styles.value}>{location.coords.longitude.toFixed(6)}</Text>
            <Text style={styles.label}>Accuracy</Text>
            <Text style={styles.value}>{location.coords.accuracy?.toFixed(1)}m</Text>
          </>
        ) : (
          <Text style={styles.waiting}>Waiting for GPS signal...</Text>
        )}
      </View>

      <View style={{ marginTop: 20, paddingHorizontal: 20 }}>
        <Button title="Logout" onPress={logout} color="#d9534f" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    paddingTop: 50,
  },
  card: {
    backgroundColor: 'white',
    marginHorizontal: 20,
    padding: 20,
    borderRadius: 15,
    marginBottom: 15,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 15,
    color: '#444',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
    paddingBottom: 5,
  },
  label: {
    fontSize: 12,
    color: '#999',
    textTransform: 'uppercase',
    marginTop: 8,
  },
  value: {
    fontSize: 16,
    color: '#333',
    fontFamily: 'monospace',
  },
  error: {
    color: '#D32F2F',
    fontSize: 14,
  },
  waiting: {
    color: '#666',
    fontStyle: 'italic',
  },
});
