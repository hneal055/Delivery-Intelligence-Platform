import { create } from 'zustand';

export const useLocationStore = create((set) => ({
  location: null,
  errorMsg: null,

  setLocation: (location) => set({ location }),
  setError: (errorMsg) => set({ errorMsg }),
}));
