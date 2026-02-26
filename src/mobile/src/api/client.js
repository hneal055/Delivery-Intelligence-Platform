import axios from 'axios';
import { Platform, Alert } from 'react-native';
import { useAuthStore } from '../stores/authStore';

// Server configuration
// Set DEV_MACHINE_IP to your backend server's LAN IP when testing on a physical device.
// iOS Simulator: use 'localhost'   |   Android Emulator: use '10.0.2.2'
// iPhone 17 on real network: use your machine's actual LAN IP (e.g. 192.168.x.x)
const DEV_MACHINE_IP = process.env.EXPO_PUBLIC_API_HOST || '192.168.12.196';
const PORT = process.env.EXPO_PUBLIC_API_PORT || '8000';

export const API_URL =
  Platform.OS === 'web'
    ? `http://localhost:${PORT}`
    : `http://${DEV_MACHINE_IP}:${PORT}`;

export const WS_URL =
  Platform.OS === 'web'
    ? `ws://localhost:${PORT}`
    : `ws://${DEV_MACHINE_IP}:${PORT}`;

const apiClient = axios.create({
  baseURL: API_URL,
  // Increased to 30 seconds for slow networks or first-time app startup
  // Real devices connecting over WiFi may experience latency
  timeout: 30000,
});

apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Log outgoing requests for debugging
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url} (timeout: ${config.timeout}ms)`);
    return config;
  },
  (error) => Promise.reject(error)
);

// Enhanced error handling with user-friendly messages
apiClient.interceptors.response.use(
  (response) => {
    console.log(`[API] ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    if (error.code === 'ECONNABORTED') {
      console.error(`[API] TIMEOUT: ${error.config.url}`);
      error.userMessage = `Request timed out. Check that:\n1. Device is on same WiFi as machine\n2. Machine IP is correct: ${DEV_MACHINE_IP}:${PORT}\n3. Backend is running`;
    } else if (error.code === 'ENOTFOUND' || error.code === 'ECONNREFUSED') {
      console.error(`[API] CONNECTION FAILED: ${error.config.url}`);
      error.userMessage = `Cannot reach backend at ${DEV_MACHINE_IP}:${PORT}.\nMake sure:\n1. WiFi is connected\n2. IP address is correct\n3. Backend is running`;
    } else if (error.response?.status === 401) {
      console.error(`[API] UNAUTHORIZED: ${error.config.url}`);
      error.userMessage = 'Invalid credentials. Check token in .env';
    } else {
      console.error(`[API] ${error.response?.status || 'ERROR'}: ${error.config.url}`, error.message);
    }
    return Promise.reject(error);
  }
);

export default apiClient;


