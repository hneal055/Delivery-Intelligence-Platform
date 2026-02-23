# Delivery Driver Mobile App

React Native (Expo) application for Delivery Intelligence Platform drivers.

## Prerequisites
- Node.js & npm
- Expo CLI (optional, can use `npx`)
- For testing:
  - **Physical Device**: Expo Go app (iOS/Android)
  - **iOS Simulator**: Xcode
  - **Android Emulator**: Android Studio

## Setup

### 1. Install Dependencies
```bash
cd src/mobile
npm install
```

### 2. Configure Backend Connection

Copy the environment template:
```bash
cp .env.example .env
```

Edit `.env` and set your backend API host:

```env
# For physical iOS/Android device on same Wi-Fi network
EXPO_PUBLIC_API_HOST=192.168.1.100  # Your PC's LAN IP

# For iOS Simulator
EXPO_PUBLIC_API_HOST=localhost

# For Android Emulator
EXPO_PUBLIC_API_HOST=10.0.2.2

EXPO_PUBLIC_API_PORT=8000
```

**Finding Your PC's IP Address:**
- **Windows**: Run `ipconfig` and look for "IPv4 Address" under your Wi-Fi adapter
- **macOS/Linux**: Run `ifconfig` or `ip addr`

### 3. Start the Backend
Ensure the backend platform is running:
```bash
cd ../..
.\start_platform.ps1  # Windows
```

## Running the App

Start Expo dev server:
```bash
npm start
```

Then choose your target:
- Press **`a`** for Android Emulator
- Press **`i`** for iOS Simulator
- Press **`w`** for Web
- Scan QR code with Expo Go for physical device

## Features
- **GPS Tracking**: Real-time location updates to dispatcher
- **Delivery Management**: View assigned packages, capture proof of delivery
- **ETA Prediction**: ML-powered arrival estimates with traffic adjustment
- **Geofence Verification**: Validates driver is at correct delivery location
- **WebSocket Communication**: Live updates from dispatch center

## Authentication
Default credentials for testing:
- Username: `driver1`
- Password: `driverpassword`

## Current Status (Feb 2026)
✅ **Core Features Working**
- Backend connectivity via environment config
- GPS tracking with consolidated location subscription
- Photo capture for proof of delivery
- WebSocket integration for real-time updates
- Performance optimized (eliminated duplicate location watchers)

✅ **Recent Fixes**
- Fixed SafeArea context error
- Resolved ImagePicker deprecation warnings
- Corrected WebSocket endpoint and message format
- Optimized scrolling performance

## Troubleshooting

### "Network Request Failed" Error
- Verify backend is running (`.\start_platform.ps1`)
- Check your `.env` file has correct IP address
- Ensure phone/emulator and PC are on same Wi-Fi network
- For physical device, disable any VPN connections

### WebSocket Connection Issues
- Confirm you're logged in (valid token)
- Check backend logs for WebSocket errors
- Verify firewall allows port 8000 connections

### Camera/Location Permissions
- iOS: Grant permissions when prompted
- Android: Check app settings if denied initially
