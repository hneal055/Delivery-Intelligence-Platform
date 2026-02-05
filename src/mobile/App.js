/* src/mobile/App.js */
import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, Button, Image, Platform, ScrollView, Alert } from 'react-native';
import * as Location from 'expo-location';
import * as ImagePicker from 'expo-image-picker';
import axios from 'axios';
import { StatusBar } from 'expo-status-bar';

// Configuration
// Use localhost for Web (Desktop)
const API_URL = Platform.OS === 'web' ? 'http://localhost:8000' : 'http://192.168.12.196:8000';
const DRIVER_ID = 'driver-mobile-001';

export default function App() {
  const [location, setLocation] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [verificationStatus, setVerificationStatus] = useState('Idle');
  const [packageId, setPackageId] = useState('PKG-12345');
  const [photo, setPhoto] = useState(null);

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
              console.log("New Location:", newLoc.coords);
          }
      );
    })();
  }, []);

  const verifyLocation = async () => {
    if (!location) {
        alert("Error: No location data available yet.");
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
            headers: { 'X-DIAD-Token': 'dev-secret-key-123' }
        });

        setVerificationStatus(response.data.message);
        if (Platform.OS === 'web') alert(response.data.message);
        else Alert.alert("API Response", response.data.message);

    } catch (error) {
        console.error(error);
        setVerificationStatus('Error connecting to API');
        if (Platform.OS === 'web') alert("Failed to verify location. Check console.");
        else Alert.alert("Error", "Failed to verify location.");
    }
  };

  const pickImage = async () => {
    let result = await ImagePicker.launchCameraAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [4, 3],
      quality: 0.5,
    });

    if (!result.canceled) {
      setPhoto(result.assets[0].uri);
    }
  };

  const confirmDelivery = async () => {
    if (!photo) {
        const msg = "Please take a proof photo first.";
        Platform.OS === 'web' ? alert(msg) : Alert.alert("Error", msg);
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
            let type = match ? `image/${match[1]}` : `image`;
            formData.append('photo', { uri: localUri, name: filename, type });
        }

        // --- FIXED SECTION START ---
        // We let axios set the Content-Type automatically so it includes the boundary
        const response = await axios.post(`${API_URL}/delivery/confirm`, formData, {
            headers: { 
                'X-DIAD-Token': 'dev-secret-key-123'
            }
        });
        // --- FIXED SECTION END ---

        const msg = "Delivery Confirmed!";
        if (Platform.OS === 'web') alert(msg);
        else Alert.alert("Success", msg);
        
        console.log(response.data);
        setPhoto(null);

    } catch (error) {
         console.error(error);
         const msg = "Delivery Confirmation Failed" + (error.response ? ": " + error.response.status : "");
         if (Platform.OS === 'web') alert(msg);
         else Alert.alert("Error", msg);
    }
  };

  return (
    <View style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.title}>Delivery Driver App</Text>
        
        <View style={styles.card}>
            <Text style={styles.subtitle}>Driver ID: {DRIVER_ID}</Text>
            <Text>Status: {errorMsg ? errorMsg : (location ? "GPS Active" : "Acquiring GPS...")}</Text>
            {location && (
                <Text style={styles.coords}>
                    {location.coords.latitude.toFixed(4)}, {location.coords.longitude.toFixed(4)}
                </Text>
            )}
        </View>

        <View style={styles.card}>
            <Text style={styles.subtitle}>Current Delivery</Text>
            <Text style={styles.pkg}>{packageId}</Text>
            <Button title="1. Verify Location" onPress={verifyLocation} />
            <Text style={styles.status}>{verificationStatus}</Text>
        </View>

        <View style={styles.card}>
            <Text style={styles.subtitle}>Proof of Delivery</Text>
            <Button title="2. Take Photo" onPress={pickImage} />
            {photo && <Image source={{ uri: photo }} style={styles.image} />}
            <View style={{marginTop: 10}}>
                <Button title="3. Confirm Delivery" onPress={confirmDelivery} disabled={!photo} color="#4CAF50" />
            </View>
        </View>

        <StatusBar style="auto" />
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
  }
});


