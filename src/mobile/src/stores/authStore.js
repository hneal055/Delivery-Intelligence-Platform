import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import AsyncStorage from '@react-native-async-storage/async-storage';

export const useAuthStore = create(
  persist(
    (set) => ({
      token: null,
      user: null,
      driverId: 'driver-mobile-001',

      login: (token, user) => set({ token, user }),
      setDriverId: (driverId) => set({ driverId }),
      logout: () => set({ token: null, user: null }),
    }),
    {
      name: 'driver-auth',
      storage: createJSONStorage(() => AsyncStorage),
    }
  )
);
