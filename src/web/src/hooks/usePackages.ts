import { useQuery } from "@tanstack/react-query";
import { listPackages } from "../api/dispatch";

export function usePackages(status?: string, driverId?: string) {
  return useQuery({
    queryKey: ["packages", status, driverId],
    queryFn: () => listPackages(status, driverId),
    refetchInterval: 30000,
  });
}
