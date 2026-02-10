# Delivery Driver Mobile App

This is the React Native (Expo) application for the Delivery Intelligence Platform drivers.

## Prerequisites
*   Node.js & npm
*   Expo CLI 
    npm install -g expo-cli (optional, can use npx)
*   Expo Go app on your physical device (Android/iOS) OR Android Studio Emulator.

## Setup

1.  Navigate to this folder:
    bash
    cd src/mobile
    

2.  Install dependencies:
    bash
    npm install
    

## Running the App

1.  Start the Expo development server:
    bash
    npm start
    # OR for web
    npx expo start --web
    

2.  **Android Emulator**: Press a.
    **iOS Simulator**: Press i.
    **Web**: Press w.
    **Physical Device**: Scan the QR code with the Expo Go app.

## Configuration
*   **API URL**: By default, the app looks for the backend at http://10.0.2.2:8000 (Android Emulator localhost alias) or http://localhost:8000 (Web).
*   If testing on a physical device, update API_URL in App.js to your computer's local network IP (e.g., http://192.168.1.5:8000).

## Current Status (Feb 2026)
- **Scaffolding**: Completed with core dependencies (Axios, Expo Camera, Expo Location).
- **Backend Connection**: Successfully verified connectivity from physical iPhone 17 to PC Backend via LAN IP (192.168.12.196).
- **Windows Support**: Applied patches for Metro Bundler on Windows (node:sea workaround).
- **Web Support**: Verified app functionality in Web browser.
- **Fixes**: Resolved template literal syntax errors in App.js and updated authentication tokens.

## Known Issues
- **Performance**: UI lag/performance issues reported during testing. Needs profiling.
- **Configuration**: API_URL and Auth Tokens are currently hardcoded in App.js. Needs to be moved to an environment variable or config file.
- **Dependencies**: React/React Native versions pinned to older stable releases to avoid Expo SDK 52 conflicts.

## Next Steps
- Implement environment variable support for dynamic IP configuration.
- Profile app performance using Flipper or React Native Performance Monitor.
