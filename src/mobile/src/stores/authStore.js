import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';
import apiClient from '../api/client';
import { setTokenProvider, setUnauthorizedHandler } from '../api/tokenProvider';

export const useAuthStore = create(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      driverId: 'driver-mobile-001',
      tokenExpiry: null,
      refreshing: false,

      login: (token, username) => {
        const expiry = new Date().getTime() + 30 * 60 * 1000;
        const num = username ? parseInt(username.replace('driver', ''), 10) : null;
        const driverId = num ? `D${String(num).padStart(3, '0')}` : get().driverId;
        set({ token, user: username, driverId, tokenExpiry: expiry });
      },

      setDriverId: (driverId) => set({ driverId }),

      logout: () => set({ token: null, user: null, tokenExpiry: null }),

      refreshTokenIfNeeded: async () => {
        const { token, tokenExpiry, refreshing } = get();
        if (!token || refreshing) return false;
        const now = new Date().getTime();
        if (tokenExpiry - now > 5 * 60 * 1000) return true;
        set({ refreshing: true });
        try {
          const response = await apiClient.post('/auth/token/refresh');
          set({ token: response.data.access_token, tokenExpiry: new Date().getTime() + 30 * 60 * 1000, refreshing: false });
          return true;
        } catch {
          set({ refreshing: false });
          return false;
        }
      },

      forceRefreshToken: async () => {
        const { token } = get();
        if (!token) return false;
        set({ refreshing: true });
        try {
          const response = await apiClient.post('/auth/token/refresh');
          set({ token: response.data.access_token, tokenExpiry: new Date().getTime() + 30 * 60 * 1000, refreshing: false });
          return true;
        } catch {
          set({ token: null, user: null, tokenExpiry: null, refreshing: false });
          return false;
        }
      },
    }),
    {
      name: 'driver-auth',
      storage: createJSONStorage(() => AsyncStorage),
    }
  )
);

// Register with tokenProvider — breaks the circular dependency:
//   client.js no longer imports authStore; it reads the token via this getter.
//   On 401, handleUnauthorized() calls logout() here, clearing stale tokens.
setTokenProvider(() => useAuthStore.getState().token);
setUnauthorizedHandler(() => useAuthStore.getState().logout());
