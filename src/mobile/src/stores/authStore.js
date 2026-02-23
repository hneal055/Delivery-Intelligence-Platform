import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';
import apiClient from '../api/client';

export const useAuthStore = create(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      driverId: 'driver-mobile-001',
      tokenExpiry: null,
      refreshing: false,

      login: (token, user) => {
        // Token typically lasts 30 minutes based on backend settings
        const expiry = new Date().getTime() + 30 * 60 * 1000;
        set({ token, user, tokenExpiry: expiry });
      },

      setDriverId: (driverId) => set({ driverId }),

      logout: () => set({ token: null, user: null, tokenExpiry: null }),

      /**
       * Refresh token if it''s expired or expiring soon (within 5 minutes)
       * Returns true if refresh succeeded, false otherwise
       */
      refreshTokenIfNeeded: async () => {
        const { token, tokenExpiry, refreshing } = get();
        
        if (!token || refreshing) return false;
        
        const now = new Date().getTime();
        const timeUntilExpiry = tokenExpiry - now;
        
        // Only refresh if token will expire within 5 minutes
        if (timeUntilExpiry > 5 * 60 * 1000) return true;
        
        set({ refreshing: true });
        
        try {
          const response = await apiClient.post('/auth/token/refresh');
          const newToken = response.data.access_token;
          const newExpiry = new Date().getTime() + 30 * 60 * 1000;
          
          set({ token: newToken, tokenExpiry: newExpiry, refreshing: false });
          return true;
        } catch (error) {
          console.warn('Token refresh failed:', error.message);
          // If refresh fails, keep existing token and let it expire naturally
          // This allows graceful degradation if backend is briefly unavailable
          set({ refreshing: false });
          return false;
        }
      },

      /**
       * Force refresh token immediately, used on app startup
       */
      forceRefreshToken: async () => {
        const { token } = get();
        
        if (!token) return false;
        
        set({ refreshing: true });
        
        try {
          const response = await apiClient.post('/auth/token/refresh');
          const newToken = response.data.access_token;
          const newExpiry = new Date().getTime() + 30 * 60 * 1000;
          
          set({ token: newToken, tokenExpiry: newExpiry, refreshing: false });
          return true;
        } catch (error) {
          console.warn('Force token refresh failed:', error.message);
          // Force refresh failure likely means token is invalid
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

