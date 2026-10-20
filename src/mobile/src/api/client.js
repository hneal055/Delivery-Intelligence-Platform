import axios from "axios";
import { Platform } from "react-native";
import Constants from "expo-constants";
import { getToken, handleUnauthorized } from "./tokenProvider";

/**
 * Use the LAN backend for development when configured; a public tunnel may be
 * unavailable locally even though the backend is running on the same Wi-Fi.
 * Production builds use EXPO_PUBLIC_API_URL when it is configured.
 */
const API_PORT = process.env.EXPO_PUBLIC_API_PORT || "8000";
const API_HOST = process.env.EXPO_PUBLIC_API_HOST;

const resolveBaseUrl = () => {
  if (__DEV__ && API_HOST) {
    return `http://${API_HOST}:${API_PORT}`;
  }
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL.replace(/\/+$/, "");
  }
  if (API_HOST) {
    return `http://${API_HOST}:${API_PORT}`;
  }

  const hostUri =
    Constants.expoConfig?.hostUri ||
    Constants.manifest2?.extra?.expoGo?.debuggerHost ||
    "";
  const hostIp = hostUri ? hostUri.split(":")[0] : null;
  const isLoopback = hostIp === "localhost" || hostIp === "127.0.0.1";

  if (__DEV__ && hostIp && !isLoopback) {
    return `http://${hostIp}:${API_PORT}`;
  }

  // Android emulators reach the host machine via 10.0.2.2
  return Platform.OS === "android"
    ? `http://10.0.2.2:${API_PORT}`
    : `http://localhost:${API_PORT}`;
};

export const BASE_URL = resolveBaseUrl();
export const API_BASE = BASE_URL;
console.log(`[API Client] baseURL: ${BASE_URL} (Platform: ${Platform.OS})`);

/** Authorization header for calls made outside axios (uploads, images). */
export function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
});

client.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    // An expired or revoked token logs the driver out; the login request
    // itself returns 401 for a wrong password, which the login screen shows.
    const isLogin = error.config?.url?.includes("/auth/token");
    if (error.response?.status === 401 && !isLogin) {
      handleUnauthorized();
    }
    return Promise.reject(error);
  }
);

/** Packages assigned to the logged-in driver (server scopes it to them). */
export async function getMyPackages() {
  const res = await client.get("/dispatch/deliveries");
  return res.data;
}

/** The logged-in driver's recent accepted proofs of delivery. */
export async function getRecentProofs(limit = 50) {
  const res = await client.get("/delivery/recent-proofs", { params: { limit } });
  return res.data;
}

/**
 * Resolve a scanned barcode (package ID or tracking code) to a package and
 * mark it loaded. Returns { package_id, package_status, dest_address }.
 */
export async function scanPackage(barcode, scanType) {
  const res = await client.post("/delivery/scan", { barcode, scan_type: scanType });
  return res.data;
}

/** Mark a package collected at its pickup point (same as scanning it). */
export async function confirmPickup(packageId) {
  return scanPackage(packageId, 'manual');
}

/** Tell dispatch this stop could not be completed, and why. */
export async function reportProblem(packageId, driverId, reason) {
  const body = new URLSearchParams({ package_id: packageId, driver_id: driverId, reason });
  const res = await client.post('/delivery/exception', body.toString(), {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  return res.data;
}

/** Send the phone's position so dispatch sees the driver on the map. */
export async function reportLocation(driverId, coords) {
  const speed = coords.speed != null && coords.speed >= 0 ? coords.speed : undefined;
  const heading = coords.heading != null && coords.heading >= 0 ? coords.heading : undefined;
  await client.post(`/tracking/${encodeURIComponent(driverId)}/location`, {
    lat: coords.latitude,
    lon: coords.longitude,
    speed,
    heading,
  });
}

/** Register this phone's Expo push token for assignment alerts. */
export async function registerDevice(token, platform) {
  await client.post('/auth/register-device', { token, platform });
}

export default client;
