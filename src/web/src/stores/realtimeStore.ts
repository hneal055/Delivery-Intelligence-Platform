import { create } from "zustand";

interface DriverLocation {
  lat: number;
  lon: number;
  speed_kmh?: number;
  heading?: number;
  timestamp: number;
}

interface RealtimeState {
  driverLocations: Record<string, DriverLocation>;
  updateDriverLocation: (driverId: string, location: DriverLocation) => void;
  removeDriver: (driverId: string) => void;
  clearAll: () => void;
}

export const useRealtimeStore = create<RealtimeState>()((set) => ({
  driverLocations: {},
  updateDriverLocation: (driverId, location) =>
    set((state) => ({
      driverLocations: {
        ...state.driverLocations,
        [driverId]: location,
      },
    })),
  removeDriver: (driverId) =>
    set((state) => {
      const { [driverId]: _, ...rest } = state.driverLocations;
      return { driverLocations: rest };
    }),
  clearAll: () => set({ driverLocations: {} }),
}));
