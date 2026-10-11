import { useEffect, useState } from "react";
import { previewAddress } from "../api/dispatch";
import type { AddressMatch } from "../types";

export type AddressStatus = "idle" | "checking" | "found" | "missing";

/** Look an address up as the dispatcher types (debounced), so the matched
 *  address is seen before the job is saved. */
export function useAddressPreview(text: string, enabled: boolean) {
  const [match, setMatch] = useState<AddressMatch | null>(null);
  const [status, setStatus] = useState<AddressStatus>("idle");
  const input = text.trim();

  useEffect(() => {
    if (!enabled || input.length < 5) {
      setMatch(null);
      setStatus("idle");
      return;
    }
    setStatus("checking");
    let cancelled = false;
    const timer = setTimeout(() => {
      previewAddress(input)
        .then((m) => {
          if (cancelled) return;
          setMatch(m);
          setStatus("found");
        })
        .catch(() => {
          if (cancelled) return;
          setMatch(null);
          setStatus("missing");
        });
    }, 600);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [input, enabled]);

  return { match, status };
}
