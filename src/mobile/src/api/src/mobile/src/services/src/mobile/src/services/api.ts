import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import { Platform } from "react-native";
import { getToken, handleUnauthorized } from "./tokenProvider";

const HOST = process.env.EXPO_PUBLIC_API_HOST || "192.168.12.196";
const PORT = process.env.EXPO_PUBLIC_API_PORT || "8002";

export const API_BASE =
  Platform.OS === "web" ? `http://localhost:${PORT}` : `http://${HOST}:${PORT}`;

export const WS_BASE =
  Platform.OS === "web" ? `ws://localhost:${PORT}` : `ws://${HOST}:${PORT}`;

const client = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

// Request Interceptor: Attach JWT Bearer Token
client.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    try {
      const token = await Promise.resolve(getToken());
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } catch (err) {
      console.warn("[API Client] Failed to resolve auth token:", err);
    }
    return config;
  },
  (error: AxiosError) => Promise.reject(error)
);

// Response Interceptor: Handle 401 Unauthorized globally
client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      console.warn("[API Client] 401 Unauthorized encountered. Purging auth state.");
      handleUnauthorized();
    }
    return Promise.reject(error);
  }
);

export default client;