import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

const ACCESS_TOKEN_KEY = "auth_access_token";
const REFRESH_TOKEN_KEY = "auth_refresh_token";

// In-memory cache for fast synchronous access in axios interceptors
let cachedAccessToken: string | null = null;
let unauthorizedListener: (() => void) | null = null;

/**
 * Register a listener function (e.g., from AuthContext or navigation)
 * to be triggered when a 401 Unauthorized response occurs.
 */
export const registerUnauthorizedHandler = (handler: () => void) => {
  unauthorizedListener = handler;
};

/**
 * Triggers the registered unauthorized handler and clears cached tokens.
 */
export const handleUnauthorized = async () => {
  await clearTokens();
  if (unauthorizedListener) {
    unauthorizedListener();
  }
};

/**
 * Retrieve the current access token.
 * Returns synchronous in-memory cached value first, with an async fallback if cache is empty.
 */
export const getToken = (): string | null => {
  return cachedAccessToken;
};

/**
 * Initialize tokens from persistent storage into memory on app startup.
 */
export const initializeTokenCache = async (): Promise<string | null> => {
  try {
    if (Platform.OS === "web") {
      cachedAccessToken = typeof window !== "undefined" ? localStorage.getItem(ACCESS_TOKEN_KEY) : null;
    } else {
      cachedAccessToken = await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
    }
  } catch (error) {
    console.error("[TokenProvider] Failed to load token from storage:", error);
    cachedAccessToken = null;
  }
  return cachedAccessToken;
};

/**
 * Persist access token (and optional refresh token) to storage and update cache.
 */
export const setTokens = async (accessToken: string, refreshToken?: string): Promise<void> => {
  cachedAccessToken = accessToken;

  try {
    if (Platform.OS === "web") {
      localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
      if (refreshToken) {
        localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
      }
    } else {
      await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken);
      if (refreshToken) {
        await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken);
      }
    }
  } catch (error) {
    console.error("[TokenProvider] Failed to persist token:", error);
  }
};

/**
 * Remove all stored tokens and purge memory cache.
 */
export const clearTokens = async (): Promise<void> => {
  cachedAccessToken = null;

  try {
    if (Platform.OS === "web") {
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(REFRESH_TOKEN_KEY);
    } else {
      await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
      await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
    }
  } catch (error) {
    console.error("[TokenProvider] Failed to clear tokens from storage:", error);
  }
};

/**
 * Retrieve refresh token if implemented.
 */
export const getRefreshToken = async (): Promise<string | null> => {
  try {
    if (Platform.OS === "web") {
      return typeof window !== "undefined" ? localStorage.getItem(REFRESH_TOKEN_KEY) : null;
    }
    return await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
  } catch (error) {
    console.error("[TokenProvider] Failed to get refresh token:", error);
    return null;
  }
};