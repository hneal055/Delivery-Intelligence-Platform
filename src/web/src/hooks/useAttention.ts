import { useQuery } from "@tanstack/react-query";
import { getAttention } from "../api/dispatch";
import type { AttentionItem } from "../types";

/** Everything dispatch should act on now; refreshed every 30 s. */
export function useAttention() {
  return useQuery({
    queryKey: ["attention"],
    queryFn: getAttention,
    refetchInterval: 30000,
  });
}

/** The button for an item: where it takes dispatch to fix it. */
export function attentionAction(item: AttentionItem): { label: string; to: string } {
  switch (item.rule) {
    case "no_driver":
      return { label: "Assign driver", to: `/scheduling?assign=${encodeURIComponent(item.job_id ?? "")}` };
    case "overdue":
      return { label: "View job", to: `/scheduling?job=${encodeURIComponent(item.job_id ?? "")}` };
    case "quiet":
    case "stopped":
      return { label: "Show on map", to: `/tracking?driver=${encodeURIComponent(item.driver_id ?? "")}` };
    default:
      return { label: "View package", to: `/packages?package=${encodeURIComponent(item.package_id ?? "")}` };
  }
}

/** "12 min ago" style age for an item's start time (UTC ISO). */
export function attentionAge(since: string | null): string | null {
  if (!since) return null;
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(since);
  const ms = Date.parse(hasZone ? since : `${since}Z`);
  if (Number.isNaN(ms)) return null;
  const minutes = Math.floor((Date.now() - ms) / 60000);
  if (minutes < 0) return `in ${Math.abs(minutes)} min`;
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  return hours < 24 ? `${hours} h ago` : `${Math.floor(hours / 24)} d ago`;
}
