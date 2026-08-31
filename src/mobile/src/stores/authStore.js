import { useState, useEffect } from "react";
import { Platform } from "react-native";
import client, { API_BASE } from "../api/client";
import { setTokenProvider, setUnauthorizedHandler } from "../api/tokenProvider";

const STORAGE_KEY = "driver-auth-state";

// In-memory state singleton
let state = {
  token: null,
  user: null,
  driverId: null,
  _hasHydrated: false,
};

const listeners = new Set();

const notify = () => {
  listeners.forEach((listener) => {
    try {
      listener(state);
    } catch (_) {}
  });
};

const set = (partial) => {
  state = { ...state, ...partial };
  notify();
};

// Safe storage wrapper without circular native import crashes
const storage = {
  async get() {
    try {
      if (Platform.OS === "web") {
        if (typeof window !== "undefined" && window.localStorage) {
          const item = window.localStorage.getItem(STORAGE_KEY);
          return item ? JSON.parse(item) : null;
        }
        return null;
      }
      const NativeStorage = require("@react-native-async-storage/async-storage").default;
      const item = await NativeStorage.getItem(STORAGE_KEY);
      return item ? JSON.parse(item) : null;
    } catch (_) {
      return null;
    }
  },
  async set(value) {
    try {
      const serialized = JSON.stringify(value);
      if (Platform.OS === "web") {
        if (typeof window !== "undefined" && window.localStorage) {
          window.localStorage.setItem(STORAGE_KEY, serialized);
        }
        return;
      }
      const NativeStorage = require("@react-native-async-storage/async-storage").default;
      await NativeStorage.setItem(STORAGE_KEY, serialized);
    } catch (_) {}
  },
  async remove() {
    try {
      if (Platform.OS === "web") {
        if (typeof window !== "undefined" && window.localStorage) {
          window.localStorage.removeItem(STORAGE_KEY);
        }
        return;
      }
      const NativeStorage = require("@react-native-async-storage/async-storage").default;
      await NativeStorage.removeItem(STORAGE_KEY);
    } catch (_) {}
  },
};

const login = async (username, password) => {
  const cleanUser = (username || "").trim();
  const cleanPass = password || "";

  const formBody = [
    `username=${encodeURIComponent(cleanUser)}`,
    `password=${encodeURIComponent(cleanPass)}`,
    `grant_type=password`,
  ].join("&");

  try {
    const endpoint = API_BASE ? `${API_BASE}/auth/token` : "/auth/token";
    console.log(`[AuthStore] Logging in '${cleanUser}' via ${endpoint}`);

    const response = await client.post("/auth/token", formBody, {
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
    });

    const token = response.data?.access_token;
    if (!token) {
      throw new Error("No access token returned by backend");
    }

    const num = parseInt(cleanUser.replace(/\D/g, ""), 10);
    const driverId = !isNaN(num) ? `D${String(num).padStart(3, "0")}` : cleanUser;

    const authData = {
      token,
      user: cleanUser,
      driverId,
    };

    await storage.set(authData);

    set({
      ...authData,
      _hasHydrated: true,
    });

    return response.data;
  } catch (err) {
    console.error("[AuthStore] Login error:", err?.response?.data || err.message);
    throw err;
  }
};

const logout = async () => {
  await storage.remove();
  set({
    token: null,
    user: null,
    driverId: null,
  });
};

const hydrate = async () => {
  const data = await storage.get();
  if (data) {
    set({
      token: data.token || null,
      user: data.user || null,
      driverId: data.driverId || null,
      _hasHydrated: true,
    });
  } else {
    set({ _hasHydrated: true });
  }
};

// Hook for components
export const useAuthStore = (selector) => {
  const [, setTick] = useState(0);

  useEffect(() => {
    const listener = () => setTick((t) => t + 1);
    listeners.add(listener);
    return () => listeners.delete(listener);
  }, []);

  const fullState = {
    ...state,
    login,
    logout,
  };

  return selector ? selector(fullState) : fullState;
};

useAuthStore.getState = () => ({
  ...state,
  login,
  logout,
});

// Run initialization
hydrate();
setTokenProvider(() => state.token);
setUnauthorizedHandler(() => logout());