import axios from 'axios';
import { Platform } from 'react-native';
import { useAuthStore } from '../stores/authStore';

// REPLACE WITH YOUR PC'S IP ADDRESS IF TESTING ON PHYSICAL DEVICE
// For Android Emulator, use '10.0.2.2'
// For iOS Simulator, use 'localhost'
const DEV_MACHINE_IP = '192.168.12.196'; 
const PORT = '8000';

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
  timeout: 10000,
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
