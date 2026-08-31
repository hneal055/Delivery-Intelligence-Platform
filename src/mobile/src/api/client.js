import axios from "axios";
import { Platform } from "react-native";
import { getToken, handleUnauthorized } from "./tokenProvider";

const HOST = process.env.EXPO_PUBLIC_API_HOST || "192.168.12.196";
const PORT = process.env.EXPO_PUBLIC_API_PORT || "8002";

// Tunnel detection
const isTunnel =
  HOST.includes("pinggy.net") ||
  HOST.includes("ngrok") ||
  HOST.includes("loca.lt") ||
  HOST.includes("trycloudflare.com");

const isSecure = PORT === "443" || isTunnel;
const httpProto = isSecure ? "https" : "http";
const wsProto = isSecure ? "wss" : "ws";

// Strip standard default ports from the host string
const portSuffix =
  PORT === "443" || PORT === "80" || isTunnel ? "" : `:${PORT}`;

// Determine base URL dynamically per platform
const getWebHost = () => {
  if (typeof window !== "undefined" && window.location?.hostname) {
    return window.location.hostname;
  }
  return "localhost";
};

export const API_BASE =
  Platform.OS === "web"
    ? `http://${getWebHost()}:${PORT}`
    : `${httpProto}://${HOST}${portSuffix}`;

export const WS_BASE =
  Platform.OS === "web"
    ? `ws://${getWebHost()}:${PORT}`
    : `${wsProto}://${HOST}${portSuffix}`;

const client = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    Accept: "application/json",
  },
});

// Request Interceptor: Attach JWT Bearer Token
client.interceptors.request.use(
  async (config) => {
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
  (error) => Promise.reject(error)
);

// Response Interceptor: Handle 401 Unauthorized globally
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      console.warn("[API Client] 401 Unauthorized encountered. Purging auth state.");
      handleUnauthorized();
    }
    return Promise.reject(error);
  }
);

export default client;