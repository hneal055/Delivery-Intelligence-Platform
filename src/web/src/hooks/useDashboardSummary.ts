import { useQuery } from "@tanstack/react-query";
import { getDashboardSummary } from "../api/dispatch";

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: getDashboardSummary,
    refetchInterval: 10000,
  });
}
