import { useQuery } from "@tanstack/react-query";
import { getJob } from "../api/dispatch";

export function useJobDetail(jobId: string | null) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId!),
    enabled: !!jobId,
  });
}
