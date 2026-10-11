import { useEffect, useState } from "react";
import apiClient from "../api/client";

/**
 * Load an image that needs the login token (proof photos). A plain <img src>
 * cannot send the Authorization header, so fetch it as a blob and show it
 * from an object URL. Returns null while loading or if it fails.
 */
export function useAuthedImage(path: string | null | undefined): string | null {
  const [src, setSrc] = useState<string | null>(null);

  useEffect(() => {
    if (!path) {
      setSrc(null);
      return;
    }
    let objectUrl: string | null = null;
    let cancelled = false;
    apiClient
      .get(path, { responseType: "blob" })
      .then((res) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(res.data as Blob);
        setSrc(objectUrl);
      })
      .catch(() => {
        if (!cancelled) setSrc(null);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [path]);

  return src;
}
