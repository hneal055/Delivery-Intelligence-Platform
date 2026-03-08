import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import AsyncStorage from "@react-native-async-storage/async-storage";
import client from "../api/client";
import { setTokenProvider, setUnauthorizedHandler } from "../api/tokenProvider";

export const useAuthStore = create(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      driverId: null,

      login: async (username, password) => {
        const form = new URLSearchParams();
        form.append("username", username);
        form.append("password", password);
        form.append("grant_type", "password");
        const res = await client.post("/auth/token", form.toString(), {
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        });
        const token = res.data.access_token;
        const num = parseInt(username.replace(/\D/g, ""), 10);
        const driverId = !isNaN(num) ? `D${String(num).padStart(3, "0")}` : username;
        set({ token, user: username, driverId });
      },

      logout: () => set({ token: null, user: null, driverId: null }),
    }),
    { name: "driver-auth", storage: createJSONStorage(() => AsyncStorage) }
  )
);

setTokenProvider(() => useAuthStore.getState().token);
setUnauthorizedHandler(() => useAuthStore.getState().logout());
