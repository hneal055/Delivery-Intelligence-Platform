import axios from "axios";
import { Platform } from "react-native";
import Constants from "expo-constants";

/**
 * Dynamically resolves the backend base URL across:
 * - Android Emulator (10.0.2.2)
 * - iOS Simulator (localhost)
 * - Physical iOS / Android devices on LAN (auto-detected via Metro hostUri)
 */
const resolveBaseUrl = () => {
  // Extract hostUri provided by Metro during development
  const hostUri =
    Constants.expoConfig?.hostUri ||
    Constants.manifest2?.extra?.expoGo?.debuggerHost ||
    "";

  const hostIp = hostUri ? hostUri.split(":")[0] : null;

  if (__DEV__ && hostIp) {
    // If the host is explicitly localhost/127.0.0.1
    const isLoopback = hostIp === "localhost" || hostIp === "127.0.0.1";

    if (Platform.OS === "android") {
      // Android emulators cannot reach host machine via 127.0.0.1; they require 10.0.2.2
      // Physical Android devices use the extracted LAN IP
      return isLoopback ? "http://10.0.2.2:8000" : `http://${hostIp}:8000`;
    }

    if (Platform.OS === "ios") {
      // iOS simulators can reach host machine via localhost
      // Physical iOS devices use the extracted LAN IP
      return isLoopback ? "http://localhost:8000" : `http://${hostIp}:8000`;
    }

    return `http://${hostIp}:8000`;
  }

  // Fallback defaults if hostUri is unavailable
  return Platform.OS === "android"
    ? "http://10.0.2.2:8000"
    : "http://localhost:8000";
};

const BASE_URL = resolveBaseUrl();
console.log(`[API Client] Initialized baseURL: ${BASE_URL} (Platform: ${Platform.OS})`);

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
});

export default client;