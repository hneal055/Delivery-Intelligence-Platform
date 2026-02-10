import React, { useState, useEffect, useCallback } from 'react';
import { View, FlatList, Text, StyleSheet, RefreshControl, ActivityIndicator } from 'react-native';
import apiClient from '../api/client';
import { useAuthStore } from '../stores/authStore';
import DeliveryCard from '../components/DeliveryCard';

export default function DeliveryListScreen({ navigation }) {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const driverId = useAuthStore((s) => s.driverId);

  const fetchPackages = useCallback(async () => {
    try {
      const response = await apiClient.get('/dispatch/packages');
      setPackages(response.data);
    } catch (error) {
      console.error('Error fetching packages:', error);
      // Show demo data if API fails
      setPackages([
        {
          id: 'PKG-12345',
          driver_id: driverId,
          dest_lat: 41.8781,
          dest_lon: -87.6298,
          dest_address: '233 S Wacker Dr, Chicago, IL',
          status: 'pending',
          predicted_eta_seconds: 1200,
        },
        {
          id: 'PKG-67890',
          driver_id: driverId,
          dest_lat: 41.8827,
          dest_lon: -87.6233,
          dest_address: '111 E Wacker Dr, Chicago, IL',
          status: 'pending',
          predicted_eta_seconds: 900,
        },
        {
          id: 'PKG-24680',
          driver_id: driverId,
          dest_lat: 41.8786,
          dest_lon: -87.6359,
          dest_address: '500 W Madison St, Chicago, IL',
          status: 'loaded',
          predicted_eta_seconds: 600,
        },
      ]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [driverId]);

  useEffect(() => {
    fetchPackages();
  }, [fetchPackages]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchPackages();
  }, [fetchPackages]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2196F3" />
        <Text style={styles.loadingText}>Loading deliveries...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={packages}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <DeliveryCard
            pkg={item}
            onPress={() => navigation.navigate('DeliveryDetail', { pkg: item })}
          />
        )}
        contentContainerStyle={styles.list}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        ListEmptyComponent={
          <Text style={styles.empty}>No deliveries assigned</Text>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  list: {
    padding: 15,
  },
  center: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    color: '#666',
  },
  empty: {
    textAlign: 'center',
    color: '#999',
    fontSize: 16,
    marginTop: 40,
  },
});
