import { useMemo } from "react";
import { useDrivers } from "./useDrivers";

/** Value used in a driver filter for "no driver assigned". */
export const UNASSIGNED = "__unassigned__";

/** Options for a "Filter by driver" select: Unassigned, then every driver. */
export function useDriverFilterOptions() {
  const { data: drivers } = useDrivers();
  return useMemo(
    () => [
      { value: UNASSIGNED, label: "Unassigned" },
      ...(drivers ?? [])
        .map((d) => ({ value: d.id, label: d.name || d.id }))
        .sort((a, b) => a.label.localeCompare(b.label)),
    ],
    [drivers]
  );
}

/** True if an item's driver_id matches the selected driver filter. */
export function matchesDriver(driverId: string | null | undefined, filter: string | null): boolean {
  if (!filter) return true;
  if (filter === UNASSIGNED) return !driverId;
  return driverId === filter;
}
