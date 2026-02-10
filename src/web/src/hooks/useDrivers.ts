import { useQuery } from "@tanstack/react-query";
import { listDrivers } from "../api/dispatch";

export function useDrivers(status?: string) {
  return useQuery({
    queryKey: ["drivers", status],
    queryFn: () => listDrivers(status),
    refetchInterval: 30000,
  });
}
