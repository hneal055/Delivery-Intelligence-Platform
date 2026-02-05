/* src/mobile/App.js */
import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, Button, Image, Platform, ScrollView, Alert } from 'react-native';
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

  const calculateEta = async () => {
    if (!location) {
        const msg = 'Acquiring GPS location...';
        Platform.OS === 'web' ? alert(msg) : Alert.alert('Wait', msg);
        return;
    }

    try {
        const destLat = location.coords.latitude + 0.05;
        const destLon = location.coords.longitude + 0.05;
        const dist = getDistanceFromLatLonInKm(
            location.coords.latitude, location.coords.longitude,
            destLat, destLon
        );

        // Match backend schema: ETARequest(distance_km, traffic_load, num_packages)
        const payload = {
            distance_km: dist,
            traffic_load: 0.8, // heavy traffic simulation
            num_packages: 5
        };

        const response = await axios.post(`${API_URL}/analytics/predict-eta`, payload, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        // Backend response: { estimated_minutes: float, ... }
        if (response.data && response.data.estimated_minutes) {
             setEta(response.data.estimated_minutes.toFixed(0));
        }

    } catch (error) {
        console.error(error);
        const msg = 'ETA Prediction Failed: ' + (error.response?.data?.detail || error.message);
        Platform.OS === 'web' ? alert(msg) : Alert.alert('Error', msg);
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

        const response = await axios.post(`${API_URL}/delivery/verify-location`, payload, {
            headers: { 'Authorization': `Bearer ${token}` }
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
        // Defensive coding for MediaType options across different Expo versions
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
            let type = match ? `image/${match[1]}` : 'image';
            formData.append('photo', { uri: localUri, name: filename, type });
        }

        const response = await axios.post(`${API_URL}/delivery/confirm`, formData, {
            headers: { 
                'Authorization': `Bearer ${token}`,
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

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>Delivery Driver App</Text>
        
        <View style={styles.card}>
            <Text style={styles.subtitle}>Driver ID: {DRIVER_ID}</Text>
            <Text>Status: {errorMsg ? errorMsg : (location ? 'GPS Active' : 'Acquiring GPS...')}</Text>
            {location && (
                <Text style={styles.coords}>
                    {location.coords.latitude.toFixed(4)}, {location.coords.longitude.toFixed(4)}
                </Text>
            )}
        </View>

        <View style={styles.card}>
            <Text style={styles.subtitle}>Current Delivery</Text>
            <Text style={styles.pkg}>{packageId}</Text>
            
            <View style={{marginBottom: 10}}>
                <Button title='Predict ETA' onPress={calculateEta} color='#2196F3' />
                {eta && <Text style={styles.etaText}>Estimated Time: {eta} mins</Text>}
            </View>

            <Button title='1. Verify Location' onPress={verifyLocation} />
            <Text style={styles.status}>{verificationStatus}</Text>
        </View>

        <View style={styles.card}>
            <Text style={styles.subtitle}>Proof of Delivery</Text>
            <Button title='2. Take Photo' onPress={pickImage} />
            {photo && <Image source={{ uri: photo }} style={styles.image} />}
            <View style={{marginTop: 10}}>
                <Button title='3. Confirm Delivery' onPress={confirmDelivery} disabled={!photo} color='#4CAF50' />
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
  },
  card: {
    backgroundColor: 'white',
    width: '90%',
    padding: 20,
    borderRadius: 10,
    marginBottom: 20,
    elevation: 3,
    ...Platform.select({
      web: {
        boxShadow: '0px 2px 2px rgba(0,0,0,0.1)',
      },
      default: {
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 2,
      },
    }),
  },
  subtitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 10,
  },
  pkg: {
    fontSize: 20,
    color: '#333',
    marginBottom: 10,
    textAlign: 'center'
  },
  coords: {
    fontFamily: 'monospace',
    marginTop: 5,
    color: '#666'
  },
  status: {
    marginTop: 10,
    fontStyle: 'italic',
    textAlign: 'center'
  },
  image: {
    width: '100%',
    height: 200,
    marginTop: 10,
    borderRadius: 5
  },
  etaText: {
    fontSize: 18,
    color: '#2196F3',
    textAlign: 'center',
    marginTop: 5,
    fontWeight: 'bold'
  }
});
