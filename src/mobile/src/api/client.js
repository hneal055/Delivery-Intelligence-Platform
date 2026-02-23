import axios from 'axios';
import { Platform } from 'react-native';
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
  // 15s covers LTE/5G latency spikes on a moving iPhone 17; still fails fast on total outages
  timeout: 15000,
});

apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default apiClient;
