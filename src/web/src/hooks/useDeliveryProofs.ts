import { useQuery } from "@tanstack/react-query";
import { getRecentProofs } from "../api/delivery";

export function useDeliveryProofs() {
  return useQuery({
    queryKey: ["delivery-proofs"],
    queryFn: getRecentProofs,
    refetchInterval: 60000,
  });
}
