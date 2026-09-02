# Android Build, Sideloading & Hardware Deployment Runbook

This document serves as the operational SOP for building, deploying, and testing the Delivery Intelligence mobile application on Android devices (commercial smartphones, Zebra TC-series, and Honeywell scanners).

---

## 1. Prerequisites & Environment Setup

- **Node.js**: v18+ or v20+
- **Expo CLI / EAS CLI**: `npm install -g eas-cli`
- **Android Debug Bridge (ADB)**: Included with Android Studio SDK Platform-Tools (`platform-tools` directory added to system `PATH`).
- **Expo Account**: Authenticated via `eas login`.

---

## 2. Configuration & Asset Requirements

### A. High-Resolution Asset Files
All icon files located in `src/mobile/assets/` must be 1024x1024 (or 1242x2436 for splash) with valid PNG CRC checksums:
- `icon.png` (1024x1024)
- `adaptive-icon.png` (1024x1024)
- `splash.png` (1242x2436)

### B. App Configuration (`app.json`)
The Android configuration block must include:
```json
"android": {
  "adaptiveIcon": {
    "foregroundImage": "./assets/adaptive-icon.png",
    "backgroundColor": "#1e293b"
  },
  "package": "com.deliveryintelligence.mobile",
  "permissions": [
    "CAMERA",
    "ACCESS_FINE_LOCATION",
    "ACCESS_COARSE_LOCATION",
    "RECEIVE_BOOT_COMPLETED",
    "VIBRATE"
  ]
}