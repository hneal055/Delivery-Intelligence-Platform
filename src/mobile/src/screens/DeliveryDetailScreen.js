import React, { useState, useEffect, useCallback } from 'react';
import {
  View, Text, Button, Image, ScrollView, StyleSheet,
  Platform, Alert, Switch,
} from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import apiClient from '../api/client';
import { useAuthStore } from '../stores/authStore';
import { useLocationStore } from '../stores/locationStore';
import { getDistanceFromLatLonInKm } from '../utils/distance';
import EtaDisplay from '../components/EtaDisplay';
import TrafficSelector from '../components/TrafficSelector';

export default function DeliveryDetailScreen({ route }) {
  const { pkg } = route.params;
  const driverId = useAuthStore((s) => s.driverId);
  const location = useLocationStore((s) => s.location);

  const [verificationStatus, setVerificationStatus] = useState('Idle');
  const [photo, setPhoto] = useState(null);
  const [eta, setEta] = useState(null);
  const [traffic, setTraffic] = useState(0.5);
  const [isAutoEta, setIsAutoEta] = useState(false);

  const calculateEta = useCallback(async () => {
    if (!location) return;
    try {
      const dist = getDistanceFromLatLonInKm(
        location.coords.latitude, location.coords.longitude,
        pkg.dest_lat, pkg.dest_lon
      );
      const response = await apiClient.post('/analytics/predict-eta', {
        distance_km: dist,
        traffic_load: traffic,
        num_packages: 5,
      });
      if (response.data?.estimated_minutes) {
        setEta(response.data.estimated_minutes.toFixed(1));
      }
    } catch (error) {
      console.error('ETA Error', error);
    }
  }, [location, traffic, pkg.dest_lat, pkg.dest_lon]);

  useEffect(() => {
    if (isAutoEta && location) {
      const timer = setTimeout(() => calculateEta(), 500);
      return () => clearTimeout(timer);
    }
  }, [location, traffic, isAutoEta, calculateEta]);

  const verifyLocation = useCallback(async () => {
    if (!location) {
      Alert.alert('No GPS Signal', 'No location data available yet. Please wait for GPS lock.');
      return;
    }
    try {
      setVerificationStatus('Checking...');
      const response = await apiClient.post('/delivery/verify-location', {
        driver_id: driverId,
        current_location: {
          lat: location.coords.latitude,
          lon: location.coords.longitude,
        },
        target_delivery_location: {
          lat: pkg.dest_lat,
          lon: pkg.dest_lon,
        },
      });
      setVerificationStatus(response.data.message);
      Alert.alert('Location Check', response.data.message);
    } catch (error) {
      console.error(error);
      setVerificationStatus('Error connecting to API');
    }
  }, [location, driverId, pkg.dest_lat, pkg.dest_lon]);

  const pickImage = useCallback(async () => {
    const { status } = await ImagePicker.requestCameraPermissionsAsync();
    if (status !== 'granted') {
      Alert.alert(
        'Camera Required',
        'Camera permission is required to capture proof of delivery.',
        [{ text: 'OK' }]
      );
      return;
    }
    try {
      const result = await ImagePicker.launchCameraAsync({
        mediaTypes: ['images'],
        allowsEditing: true,
        aspect: [4, 3],
        quality: 0.5,
      });
      if (!result.canceled) {
        setPhoto(result.assets[0].uri);
      }
    } catch (error) {
      console.error('Camera Error:', error);
    }
  }, []);

  const confirmDelivery = useCallback(async () => {
    if (!photo) {
      Alert.alert('Photo Required', 'Please take a proof photo first.');
      return;
    }
    try {
      const formData = new FormData();
      formData.append('package_id', pkg.id);
      formData.append('driver_id', driverId);

      const localUri = photo;
      const filename = localUri.split('/').pop();

      if (Platform.OS === 'web') {
        const res = await fetch(localUri);
        const blob = await res.blob();
        formData.append('photo', blob, filename || 'upload.jpg');
      } else {
        const match = /\.(\w+)$/.exec(filename);
        const type = match ? `image/${match[1]}` : 'image/jpeg';
        formData.append('photo', { uri: localUri, name: filename, type });
      }

      await apiClient.post('/delivery/confirm', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      Alert.alert('Success', 'Delivery Confirmed!');
      setPhoto(null);
    } catch (error) {
      console.error(error);
      Alert.alert('Error', 'Delivery Confirmation Failed. Please try again.');
    }
  }, [photo, pkg.id, driverId]);

  const reportException = useCallback(async () => {
    try {
      const formData = new FormData();
      formData.append('package_id', pkg.id);
      formData.append('driver_id', driverId);
      formData.append('reason', 'Customer Unavailable');

      await apiClient.post('/delivery/exception', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      Alert.alert('Reported', 'Exception reported.');
    } catch (error) {
      console.error(error);
      Alert.alert('Error', 'Failed to report exception.');
    }
  }, [pkg.id, driverId]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.card}>
        <Text style={styles.subtitle}>Smart ETA Prediction</Text>
        <View style={styles.row}>
          <Text>Auto-Update:</Text>
          <Switch value={isAutoEta} onValueChange={setIsAutoEta} />
        </View>
        <TrafficSelector traffic={traffic} onTrafficChange={setTraffic} />
        <EtaDisplay eta={eta} />
        <Button title="Calculate ETA" onPress={calculateEta} />
      </View>

      <View style={styles.card}>
        <Text style={styles.subtitle}>Package: {pkg.id}</Text>
        <Text style={styles.address}>
          {pkg.dest_address || `${pkg.dest_lat.toFixed(4)}, ${pkg.dest_lon.toFixed(4)}`}
        </Text>
        {location && (
          <Text style={styles.coords}>
            GPS: {location.coords.latitude.toFixed(4)}, {location.coords.longitude.toFixed(4)}
          </Text>
        )}
      </View>

      <View style={styles.card}>
        <Text style={styles.subtitle}>Delivery Actions</Text>
        <View style={{ marginBottom: 10 }}>
          <Button title="Verify GPS Location" onPress={verifyLocation} color="#607D8B" />
          <Text style={styles.status}>{verificationStatus}</Text>
        </View>

        <Button title="Capture Proof of Delivery" onPress={pickImage} />
        {photo && <Image source={{ uri: photo }} style={styles.image} resizeMode="cover" />}

        <View style={{ marginTop: 10 }}>
          <Button
            title="Confirm Delivery"
            onPress={confirmDelivery}
            disabled={!photo}
            color="#4CAF50"
          />
        </View>
        <View style={{ marginTop: 10 }}>
          <Button title="Report Exception" color="#D32F2F" onPress={reportException} />
        </View>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  content: {
    padding: 15,
    paddingBottom: 40,
  },
  card: {
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 15,
    marginBottom: 15,
    elevation: 4,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
  },
  subtitle: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 15,
    color: '#444',
    borderBottomWidth: 1,
    borderBottomColor: '#eee',
    paddingBottom: 5,
  },
  address: {
    fontSize: 14,
    color: '#333',
    marginBottom: 5,
  },
  coords: {
    fontFamily: 'monospace',
    marginTop: 5,
    color: '#666',
    fontSize: 12,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  status: {
    marginTop: 5,
    fontStyle: 'italic',
    textAlign: 'center',
    marginBottom: 10,
  },
  image: {
    width: '100%',
    height: 200,
    marginTop: 10,
    borderRadius: 8,
    backgroundColor: '#eee',
  },
});
