import { useQuery } from "@tanstack/react-query";
import { getLocationHistory } from "../api/dispatch";

export function useLocationHistory(driverId: string | null, hours: number = 24) {
  return useQuery({
    queryKey: ["locationHistory", driverId, hours],
    queryFn: () => getLocationHistory(driverId!, hours),
    enabled: !!driverId,
  });
}
