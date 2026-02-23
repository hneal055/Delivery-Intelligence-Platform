// src/mobile/src/components/NavigationButtons.js
// UI component for navigation button options

import React, { useState, useEffect } from 'react';
import {
  View, Button, StyleSheet, Text, ActivityIndicator,
  ScrollView, Dimensions
} from 'react-native';
import navigationService from '../services/navigationService';

export default function NavigationButtons({ latitude, longitude, address }) {
  const [availableApps, setAvailableApps] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkApps() {
      try {
        const apps = await navigationService.getAvailableNavApps();
        setAvailableApps(apps);
      } catch (error) {
        console.error('Error checking nav apps:', error);
      } finally {
        setLoading(false);
      }
    }
    checkApps();
  }, []);

  const handleNavigate = async (app) => {
    const success = await navigationService.navigateTo(
      latitude,
      longitude,
      address,
      app === 'web-fallback' ? 'auto' : app
    );
    
    if (!success) {
      console.warn(\Failed to open \\);
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="small" color="#2196F3" />
        <Text style={styles.loadingText}>Checking navigation apps...</Text>
      </View>
    );
  }

  const icons = {
    waze: '🧭',
    google: '📍',
    apple: '🗺️',
    'web-fallback': '🌐',
  };

  const labels = {
    waze: 'Waze',
    google: 'Google Maps',
    apple: 'Apple Maps',
    'web-fallback': 'Maps',
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Navigate To:</Text>
      <Text style={styles.address}>{address}</Text>
      
      <ScrollView 
        horizontal 
        showsHorizontalScrollIndicator={false}
        style={styles.buttonContainer}
      >
        {availableApps.map((app) => (
          <View key={app} style={styles.buttonWrapper}>
            <Button
              title={\\ \\}
              onPress={() => handleNavigate(app)}
              color="#2196F3"
            />
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 15,
    elevation: 3,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 5,
    color: '#333',
  },
  address: {
    fontSize: 13,
    color: '#666',
    marginBottom: 12,
    fontStyle: 'italic',
  },
  loadingContainer: {
    backgroundColor: 'white',
    padding: 15,
    borderRadius: 10,
    marginBottom: 15,
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    marginTop: 8,
    fontSize: 13,
    color: '#666',
  },
  buttonContainer: {
    flexDirection: 'row',
  },
  buttonWrapper: {
    marginRight: 10,
    minWidth: 100,
  },
});
