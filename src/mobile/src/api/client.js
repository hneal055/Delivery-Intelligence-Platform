import axios from "axios";
import { Platform } from "react-native";
import { getToken, handleUnauthorized } from "./tokenProvider";

const HOST = process.env.EXPO_PUBLIC_API_HOST || "192.168.12.195";
const PORT = process.env.EXPO_PUBLIC_API_PORT || "8002";

export const API_BASE =
  Platform.OS === "web" ? `http://localhost:${PORT}` : `http://${HOST}:${PORT}`;
export const WS_BASE =
  Platform.OS === "web" ? `ws://localhost:${PORT}` : `ws://${HOST}:${PORT}`;

const client = axios.create({ baseURL: API_BASE, timeout: 30000 });

client.interceptors.request.use((config) => {
  const token = getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) handleUnauthorized();
    return Promise.reject(err);
  }
);

export default client;
