import React, { useState, useEffect, useCallback } from 'react';
import { StyleSheet, Text, View, Button, Image, Platform, ScrollView, Alert, TouchableOpacity, Switch } from 'react-native';
import * as Location from 'expo-location';
import * as ImagePicker from 'expo-image-picker';
import axios from 'axios';
import { StatusBar } from 'expo-status-bar';
import LoginScreen from './screens/LoginScreen';

// Configuration
// Use localhost for Web (Desktop)
const API_URL = Platform.OS === 'web' ? 'http://localhost:8000' : 'http://192.168.12.196:8000';
const DRIVER_ID = 'driver-mobile-001';

// Helper to calculate distance in km between two coords
function getDistanceFromLatLonInKm(lat1, lon1, lat2, lon2) {
  var R = 6371; // Radius of the earth in km
  var dLat = deg2rad(lat2-lat1);  // deg2rad below
  var dLon = deg2rad(lon2-lon1); 
  var a = 
    Math.sin(dLat/2) * Math.sin(dLat/2) +
    Math.cos(deg2rad(lat1)) * Math.cos(deg2rad(lat2)) * 
    Math.sin(dLon/2) * Math.sin(dLon/2)
    ; 
  var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a)); 
  var d = R * c; // Distance in km
  return d;
}

function deg2rad(deg) {
  return deg * (Math.PI/180)
}

export default function App() {
  const [token, setToken] = useState(null);
  const [location, setLocation] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [verificationStatus, setVerificationStatus] = useState('Idle');
  const [packageId, setPackageId] = useState('PKG-12345');
  const [photo, setPhoto] = useState(null);
  const [eta, setEta] = useState(null);
  
  // New State for ML Inputs
  const [traffic, setTraffic] = useState(0.5); // 0.0 to 1.0
  const [isAutoEta, setIsAutoEta] = useState(true);

  useEffect(() => {
    (async () => {
      let { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        setErrorMsg('Permission to access location was denied');
        return;
      }

      Location.watchPositionAsync(
          { accuracy: Location.Accuracy.High, timeInterval: 5000, distanceInterval: 10 },
          (newLoc) => {
              setLocation(newLoc);
              console.log('New Location:', newLoc.coords);
          }
      );
    })();
  }, []);

  // Real-time ETA Update Effect
  useEffect(() => {
    if (isAutoEta && location && token) {
        // Debounce slightly to prevent spamming
        const timer = setTimeout(() => {
            calculateEta();
        }, 500); 
        return () => clearTimeout(timer);
    }
  }, [location, traffic, isAutoEta, token]);

  const calculateEta = async () => {
    if (!location) return;

    try {
        // Simulated destination (just slightly offset)
        const destLat = location.coords.latitude + 0.05;
        const destLon = location.coords.longitude + 0.05;
        const dist = getDistanceFromLatLonInKm(
            location.coords.latitude, location.coords.longitude,
            destLat, destLon
        );

        // Match backend schema: ETARequest(distance_km, traffic_load, num_packages)
        const payload = {
            distance_km: dist,
            traffic_load: traffic,
            num_packages: 5
        };

        const response = await axios.post(${API_URL}/analytics/predict-eta, payload, {
            headers: { 'Authorization': Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbl91c2VyIiwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzcwMzU5NDk3fQ.23y4ZQDvtPrrnOaaKaPSnaeDUa9P36x5xEHjtfNS_7w }
        });

        // Backend response: { estimated_minutes: float, ... }
        if (response.data && response.data.estimated_minutes) {
             setEta(response.data.estimated_minutes.toFixed(1)); // More precision
        }

    } catch (error) {
        console.error('ETA Error', error);
        // Silent fail for auto-updates, only alert on manual checks? 
        // For now just log to avoid spamming alerts in real-time mode
        if (!isAutoEta) {
             const msg = 'ETA Prediction Failed: ' + (error.response?.data?.detail || error.message);
             Platform.OS === 'web' ? alert(msg) : Alert.alert('Error', msg);
        }
    }
  };

  const verifyLocation = async () => {
    if (!location) {
        alert('Error: No location data available yet.');
        return;
    }

    try {
        setVerificationStatus('Checking...');
        
        const target = {
            lat: location.coords.latitude, 
            lon: location.coords.longitude
        };

        const payload = {
            driver_id: DRIVER_ID,
            current_location: { lat: location.coords.latitude, lon: location.coords.longitude },
            target_delivery_location: target 
        };

        const response = await axios.post(${API_URL}/delivery/verify-location, payload, {
            headers: { 'Authorization': Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbl91c2VyIiwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzcwMzU5NDk3fQ.23y4ZQDvtPrrnOaaKaPSnaeDUa9P36x5xEHjtfNS_7w }
        });

        setVerificationStatus(response.data.message);
        if (Platform.OS === 'web') alert(response.data.message);
        else Alert.alert('API Response', response.data.message);

    } catch (error) {
        console.error(error);
        setVerificationStatus('Error connecting to API');
        if (Platform.OS === 'web') alert('Failed to verify location. Check console.');
        else Alert.alert('Error', 'Failed to verify location. ' + (error.response?.status || ''));
    }
  };

  const pickImage = async () => {
    try {
        const mediaTypes = ImagePicker.MediaTypeOptions?.Images || ImagePicker.MediaType?.Images || 'Images';
        
        let result = await ImagePicker.launchCameraAsync({
            mediaTypes: mediaTypes,
            allowsEditing: true,
            aspect: [4, 3],
            quality: 0.5,
        });

        if (!result.canceled) {
            setPhoto(result.assets[0].uri);
        }
    } catch (error) {
        console.error('Camera Error:', error);
        if (Platform.OS === 'web') alert('Camera Error: ' + error.message);
        else Alert.alert('Camera Error', error.message);
    }
  };

  const confirmDelivery = async () => {
    if (!photo) {
        const msg = 'Please take a proof photo first.';
        Platform.OS === 'web' ? alert(msg) : Alert.alert('Error', msg);
        return;
    }

    try {
        const formData = new FormData();
        formData.append('package_id', packageId);
        formData.append('driver_id', DRIVER_ID);
        
        let localUri = photo;
        let filename = localUri.split('/').pop();
        
        if (Platform.OS === 'web') {
            const res = await fetch(localUri);
            const blob = await res.blob();
            formData.append('photo', blob, filename || 'upload.jpg');
        } else {
            let match = /\.(\w+)$/.exec(filename);
            let type = match ? image/ : 'image';
            formData.append('photo', { uri: localUri, name: filename, type });
        }

        const response = await axios.post(${API_URL}/delivery/confirm, formData, {
            headers: { 
                'Authorization': Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbl91c2VyIiwicm9sZSI6ImFkbWluIiwiZXhwIjoxNzcwMzU5NDk3fQ.23y4ZQDvtPrrnOaaKaPSnaeDUa9P36x5xEHjtfNS_7w,
                'Content-Type': 'multipart/form-data',
            }
        });

        const msg = 'Delivery Confirmed!';
        if (Platform.OS === 'web') alert(msg);
        else Alert.alert('Success', msg);
        
        console.log(response.data);
        setPhoto(null);

    } catch (error) {
         console.error(error);
         const msg = 'Delivery Confirmation Failed' + (error.response ? ': ' + error.response.status : '');
         if (Platform.OS === 'web') alert(msg);
         else Alert.alert('Error', msg);
    }
  };

  if (!token) {
      return <LoginScreen onLogin={setToken} apiUrl={API_URL} />;
  }

  // Helper for traffic button
  const TrafficButton = ({ level, label, value }) => (
    <TouchableOpacity 
        style={[styles.trafficBtn, traffic === value && styles.trafficBtnActive]}
        onPress={() => setTraffic(value)}
    >
        <Text style={[styles.trafficBtnText, traffic === value && styles.trafficBtnTextActive]}>
            {label}
        </Text>
    </TouchableOpacity>
  );

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>Delivery Intelligence</Text>
        
        <View style={styles.card}>
            <Text style={styles.subtitle}>Smart ETA Prediction</Text>
            
            <View style={styles.row}>
                <Text>Auto-Update:</Text>
                <Switch value={isAutoEta} onValueChange={setIsAutoEta} />
            </View>

            <Text style={styles.label}>Current Traffic Conditions:</Text>
            <View style={styles.trafficRow}>
                <TrafficButton label='Light' value={0.1} />
                <TrafficButton label='Moderate' value={0.5} />
                <TrafficButton label='Heavy' value={0.9} />
            </View>

            {eta ? (
                <View style={styles.etaContainer}>
                     <Text style={styles.etaLabel}>Estimated Arrival</Text>
                     <Text style={styles.etaValue}>{eta} <Text style={{fontSize: 20}}>min</Text></Text>
                     <Text style={styles.etaNote}>(ML Model Confidence: High)</Text>
                </View>
            ) : (
                <Text style={{textAlign: 'center', margin: 20}}>Calculating Route...</Text>
            )}

            {!isAutoEta && <Button title='Refresh ETA' onPress={calculateEta} />}
        </View>

        <View style={styles.card}>
            <Text style={styles.subtitle}>Driver ID: {DRIVER_ID}</Text>
            <Text style={styles.pkg}>Current Package: {packageId}</Text>
            {location && (
                <Text style={styles.coords}>
                    GPS: {location.coords.latitude.toFixed(4)}, {location.coords.longitude.toFixed(4)}
                </Text>
            )}
        </View>

        <View style={styles.card}>
            <Text style={styles.subtitle}>Delivery Actions</Text>
            <View style={{marginBottom: 10}}>
                 <Button title='Verify GPS Location' onPress={verifyLocation} color='#607D8B' />
                 <Text style={styles.status}>{verificationStatus}</Text>
            </View>
            
            <Button title='Capture Proof of Delivery' onPress={pickImage} />
            {photo && <Image source={{ uri: photo }} style={styles.image} />}
            
            <View style={{marginTop: 10}}>
                <Button title='Confirm Delivery' onPress={confirmDelivery} disabled={!photo} color='#4CAF50' />
            </View>
        </View>

        <Button title='Logout' onPress={() => setToken(null)} color='#d9534f' />
        <StatusBar style='auto' />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
    paddingTop: 50,
  },
  scroll: {
    alignItems: 'center',
    paddingBottom: 40
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    color: '#333'
  },
  card: {
    backgroundColor: 'white',
    width: '90%',
    padding: 20,
    borderRadius: 15,
    marginBottom: 20,
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
    paddingBottom: 5
  },
  pkg: {
    fontSize: 18,
    color: '#333',
    marginBottom: 5,
  },
  coords: {
    fontFamily: 'monospace',
    marginTop: 5,
    color: '#666',
    fontSize: 12
  },
  status: {
    marginTop: 5,
    fontStyle: 'italic',
    textAlign: 'center',
    marginBottom: 10
  },
  image: {
    width: '100%',
    height: 200,
    marginTop: 10,
    borderRadius: 8,
    backgroundColor: '#eee'
  },
  etaContainer: {
    alignItems: 'center',
    marginVertical: 20,
    backgroundColor: '#E3F2FD',
    padding: 15,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#2196F3'
  },
  etaLabel: {
    color: '#1976D2',
    fontSize: 14,
    fontWeight: '600',
    textTransform: 'uppercase'
  },
  etaValue: {
    fontSize: 48,
    fontWeight: 'bold',
    color: '#0D47A1'
  },
  etaNote: {
      fontSize: 12,
      color: '#555',
      marginTop: 5
  },
  row: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: 10
  },
  trafficRow: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      marginVertical: 10
  },
  trafficBtn: {
      flex: 1,
      padding: 10,
      alignItems: 'center',
      backgroundColor: '#f0f0f0',
      marginHorizontal: 2,
      borderRadius: 5
  },
  trafficBtnActive: {
      backgroundColor: '#FF9800'
  },
  trafficBtnText: {
      color: '#333',
      fontSize: 12
  },
  trafficBtnTextActive: {
      color: 'white',
      fontWeight: 'bold'
  },
  label: {
      fontSize: 14,
      color: '#666',
      marginTop: 5
  }
});

