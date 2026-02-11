import { Paper, Button, Text, Stack, Alert, Badge, Group, Center } from "@mantine/core";
import { IconScan, IconX } from "@tabler/icons-react";
import { useBarcodeScanner } from "../../hooks/useBarcodeScanner";

interface BarcodeScannerProps {
  onDetected: (barcode: string) => void;
}

export function BarcodeScanner({ onDetected }: BarcodeScannerProps) {
  const { videoRef, isScanning, startScan, stopScan, lastBarcode, error } = useBarcodeScanner({
    onDetected,
  });

  return (
    <Stack gap="sm">
      <Paper
        radius="md"
        withBorder
        style={{
          position: "relative",
          overflow: "hidden",
          background: "#000",
          minHeight: 240,
        }}
      >
        <video
          ref={videoRef}
          style={{
            width: "100%",
            height: 240,
            objectFit: "cover",
            display: isScanning ? "block" : "none",
          }}
          muted
          playsInline
        />

        {!isScanning && (
          <Center style={{ height: 240 }}>
            <Stack align="center" gap="xs">
              <IconScan size={48} color="gray" />
              <Text c="dimmed" size="sm">
                Click Start to begin scanning
              </Text>
            </Stack>
          </Center>
        )}

        {isScanning && (
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: "10%",
              right: "10%",
              height: 2,
              background: "red",
              boxShadow: "0 0 8px rgba(255,0,0,0.6)",
              animation: "scanLine 2s ease-in-out infinite",
            }}
          />
        )}
      </Paper>

      <Group justify="center" gap="sm">
        {!isScanning ? (
          <Button leftSection={<IconScan size={16} />} onClick={startScan}>
            Start Scanner
          </Button>
        ) : (
          <Button color="red" leftSection={<IconX size={16} />} onClick={stopScan}>
            Stop Scanner
          </Button>
        )}
      </Group>

      {lastBarcode && (
        <Group gap="xs">
          <Text size="sm" fw={500}>Last scanned:</Text>
          <Badge color="green" size="lg">{lastBarcode}</Badge>
        </Group>
      )}

      {error && (
        <Alert color="red" variant="light">
          {error}
        </Alert>
      )}

      <style>{`
        @keyframes scanLine {
          0%, 100% { transform: translateY(-40px); }
          50% { transform: translateY(40px); }
        }
      `}</style>
    </Stack>
  );
}
