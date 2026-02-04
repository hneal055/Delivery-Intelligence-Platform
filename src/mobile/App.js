import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View, Button, Image, Platform, ScrollView, Alert } from 'react-native';
import * as Location from 'expo-location';
import * as ImagePicker from 'expo-image-picker';
import axios from 'axios';
import { StatusBar } from 'expo-status-bar';

// Configuration
// Ideally use environment variables, but for demo:
// Android Emulator uses 10.0.2.2 for localhost
const API_URL = Platform.OS === 'android' ? 'http://192.168.12.139:8000' : 'http://192.168.12.139:8000';
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

      // Start watching position
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
        Alert.alert("Error", "No location data available yet.");
        return;
    }

    try {
        setVerificationStatus('Checking...');
        // Mock target location (e.g. 50m away from simulator default)
        // For testing, let's use the current location slightly offset so it passes or fails
        const target = {
            lat: location.coords.latitude, 
            lon: location.coords.longitude
        };

        const payload = {
            driver_id: DRIVER_ID,
            current_location: { lat: location.coords.latitude, lon: location.coords.longitude },
            target_delivery_location: target 
        };

        const response = await axios.post(\\/delivery/verify-location\, payload, {
            headers: { 'X-DIAD-Token': 'dev-secret-key-123' }
        });

        setVerificationStatus(response.data.message);
        Alert.alert("API Response", response.data.message);

    } catch (error) {
        console.error(error);
        setVerificationStatus('Error connecting to API');
        Alert.alert("Error", "Failed to verify location.");
    }
  };

  const pickImage = async () => {
    // No permissions request is necessary for launching the image library
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
        Alert.alert("Error", "Please take a proof photo first.");
        return;
    }

    try {
        const formData = new FormData();
        formData.append('package_id', packageId);
        formData.append('driver_id', DRIVER_ID);
        
        // Append file
        let localUri = photo;
        let filename = localUri.split('/').pop();
        let match = /\.(\w+)$/.exec(filename);
        let type = match ? \image/\\ : \image\;

        formData.append('photo', { uri: localUri, name: filename, type });

        const response = await axios.post(\\/delivery/confirm\, formData, {
            headers: { 
                'Content-Type': 'multipart/form-data',
                'X-DIAD-Token': 'dev-secret-key-123'
            }
        });

        Alert.alert("Success", "Delivery Confirmed!");
        console.log(response.data);
        setPhoto(null);

    } catch (error) {
         console.error(error);
         Alert.alert("Error", "Delivery Confirmation Failed" + (error.response ? ": " + error.response.status : ""));
    }
  };

  /* ... Styles ... */
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
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
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

