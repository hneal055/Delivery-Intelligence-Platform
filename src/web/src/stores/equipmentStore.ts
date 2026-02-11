import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Equipment, EquipmentScanEvent } from "../types";

interface EquipmentState {
  equipment: Equipment[];
  scanEvents: EquipmentScanEvent[];
  addEquipment: (item: Equipment) => void;
  updateEquipment: (id: string, updates: Partial<Equipment>) => void;
  removeEquipment: (id: string) => void;
  checkOut: (equipmentId: string, driverId: string) => void;
  checkIn: (equipmentId: string) => void;
  findByBarcode: (barcode: string) => Equipment | undefined;
}

export const useEquipmentStore = create<EquipmentState>()(
  persist(
    (set, get) => ({
      equipment: [],
      scanEvents: [],

      addEquipment: (item) =>
        set((state) => ({ equipment: [...state.equipment, item] })),

      updateEquipment: (id, updates) =>
        set((state) => ({
          equipment: state.equipment.map((e) =>
            e.id === id ? { ...e, ...updates } : e
          ),
        })),

      removeEquipment: (id) =>
        set((state) => ({
          equipment: state.equipment.filter((e) => e.id !== id),
        })),

      checkOut: (equipmentId, driverId) => {
        const now = new Date().toISOString();
        const item = get().equipment.find((e) => e.id === equipmentId);
        if (!item) return;

        set((state) => ({
          equipment: state.equipment.map((e) =>
            e.id === equipmentId
              ? { ...e, status: "checked_out" as const, checked_out_by: driverId, checked_out_at: now }
              : e
          ),
          scanEvents: [
            {
              equipment_id: equipmentId,
              barcode: item.barcode,
              action: "check_out" as const,
              driver_id: driverId,
              timestamp: now,
            },
            ...state.scanEvents,
          ].slice(0, 100), // keep last 100 events
        }));
      },

      checkIn: (equipmentId) => {
        const now = new Date().toISOString();
        const item = get().equipment.find((e) => e.id === equipmentId);
        if (!item) return;

        set((state) => ({
          equipment: state.equipment.map((e) =>
            e.id === equipmentId
              ? { ...e, status: "available" as const, checked_out_by: null, checked_out_at: null }
              : e
          ),
          scanEvents: [
            {
              equipment_id: equipmentId,
              barcode: item.barcode,
              action: "check_in" as const,
              driver_id: item.checked_out_by ?? "unknown",
              timestamp: now,
            },
            ...state.scanEvents,
          ].slice(0, 100),
        }));
      },

      findByBarcode: (barcode) => get().equipment.find((e) => e.barcode === barcode),
    }),
    { name: "equipment-store" }
  )
);
