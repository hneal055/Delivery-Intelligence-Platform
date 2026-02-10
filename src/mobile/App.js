import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { StatusBar } from 'expo-status-bar';
import AppNavigator from './src/navigation/AppNavigator';
import { useLocation } from './src/hooks/useLocation';

function LocationTracker() {
  // Initialize GPS tracking at app level so it's always running
  useLocation();
  return null;
}

export default function App() {
  return (
    <NavigationContainer>
      <LocationTracker />
      <AppNavigator />
      <StatusBar style="auto" />
    </NavigationContainer>
  );
}
