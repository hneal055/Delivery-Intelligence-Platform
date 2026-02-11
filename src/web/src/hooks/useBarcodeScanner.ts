import { useRef, useState, useCallback, useEffect } from "react";

interface UseBarcodeOptions {
  onDetected?: (barcode: string) => void;
}

export function useBarcodeScanner(options?: UseBarcodeOptions) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const animRef = useRef<number>(0);
  const [isScanning, setIsScanning] = useState(false);
  const [lastBarcode, setLastBarcode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const lastDetectedRef = useRef<string>("");
  const lastDetectedTimeRef = useRef<number>(0);

  const stopScan = useCallback(() => {
    cancelAnimationFrame(animRef.current);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsScanning(false);
  }, []);

  const startScan = useCallback(async () => {
    setError(null);
    setLastBarcode(null);

    // Check for BarcodeDetector API
    const BarcodeDetectorClass =
      (window as unknown as { BarcodeDetector?: typeof BarcodeDetector }).BarcodeDetector;

    if (!BarcodeDetectorClass) {
      // Try dynamic import of polyfill
      try {
        const mod = await import("barcode-detector");
        (window as unknown as { BarcodeDetector: typeof BarcodeDetector }).BarcodeDetector =
          mod.BarcodeDetector as unknown as typeof BarcodeDetector;
      } catch {
        setError("Barcode scanning is not supported in this browser.");
        return;
      }
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      setIsScanning(true);

      const detector = new (
        (window as unknown as { BarcodeDetector: typeof BarcodeDetector }).BarcodeDetector
      )({ formats: ["qr_code", "code_128", "ean_13", "ean_8", "code_39"] });

      const scan = async () => {
        if (!videoRef.current || !streamRef.current) return;

        try {
          const barcodes = await detector.detect(videoRef.current);
          if (barcodes.length > 0) {
            const code = barcodes[0].rawValue;
            const now = Date.now();
            // Debounce: ignore same code within 2 seconds
            if (code !== lastDetectedRef.current || now - lastDetectedTimeRef.current > 2000) {
              lastDetectedRef.current = code;
              lastDetectedTimeRef.current = now;
              setLastBarcode(code);
              options?.onDetected?.(code);
            }
          }
        } catch {
          // Detection frame error, continue scanning
        }

        animRef.current = requestAnimationFrame(scan);
      };

      animRef.current = requestAnimationFrame(scan);
    } catch (err) {
      setError("Camera access denied or not available.");
      setIsScanning(false);
    }
  }, [options]);

  useEffect(() => {
    return () => {
      cancelAnimationFrame(animRef.current);
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  return { videoRef, isScanning, startScan, stopScan, lastBarcode, error };
}
