# Delivery Driver Mobile App

This is the React Native (Expo) application for the Delivery Intelligence Platform drivers.

## Prerequisites
*   Node.js & npm
*   Expo CLI 
pm install -g expo-cli (optional, can use npx)
*   Expo Go app on your physical device (Android/iOS) OR Android Studio Emulator.

## Setup

1.  Navigate to this folder:
    \\\ash
    cd src/mobile
    \\\

2.  Install dependencies:
    \\\ash
    npm install
    \\\

## Running the App

1.  Start the Expo development server:
    \\\ash
    npm start
    \\\

2.  **Android Emulator**: Press \\.
    **iOS Simulator**: Press \i\.
    **Physical Device**: Scan the QR code with the Expo Go app.

## Configuration
*   **API URL**: By default, the app looks for the backend at \http://10.0.2.2:8000\ (Android Emulator localhost alias).
*   If testing on a physical device, update \API_URL\ in \App.js\ to your computer's local network IP (e.g., \http://192.168.1.5:8000\).
