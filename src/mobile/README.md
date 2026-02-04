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

## Current Status (Feb 2026)
- **Scaffolding**: Completed with core dependencies (Axios, Expo Camera, Expo Location).
- **Backend Connection**: Successfully verified connectivity from physical iPhone 17 to PC Backend via LAN IP (192.168.12.196).
- **Windows Support**: Applied patches for Metro Bundler on Windows (node:sea workaround).

## Known Issues
- **Performance**: UI lag/performance issues reported during testing. Needs profiling.
- **Configuration**: API_URL is currently hardcoded in App.js. Needs to be moved to an environment variable or config file.
- **Dependencies**: React/React Native versions pinned to older stable releases to avoid Expo SDK 52 conflicts.

## Next Steps
- Implement environment variable support for dynamic IP configuration.
- Profile app performance using Flipper or React Native Performance Monitor.
- Refactor App.js into smaller components.

