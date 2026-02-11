import { useState } from "react";
import { Modal, Stack, Text, Badge, Button, Group, TextInput, Alert } from "@mantine/core";
import { IconLogin, IconLogout } from "@tabler/icons-react";
import { BarcodeScanner } from "./BarcodeScanner";
import { useEquipmentStore } from "../../stores/equipmentStore";

interface EquipmentCheckModalProps {
  opened: boolean;
  onClose: () => void;
  driverId: string;
}

export function EquipmentCheckModal({ opened, onClose, driverId }: EquipmentCheckModalProps) {
  const [scannedBarcode, setScannedBarcode] = useState<string | null>(null);
  const [manualBarcode, setManualBarcode] = useState("");
  const findByBarcode = useEquipmentStore((s) => s.findByBarcode);
  const checkIn = useEquipmentStore((s) => s.checkIn);
  const checkOut = useEquipmentStore((s) => s.checkOut);

  const barcode = scannedBarcode ?? (manualBarcode || null);
  const matchedItem = barcode ? findByBarcode(barcode) : undefined;

  const handleAction = (action: "check_in" | "check_out") => {
    if (!matchedItem) return;
    if (action === "check_in") {
      checkIn(matchedItem.id);
    } else {
      checkOut(matchedItem.id, driverId);
    }
    handleClose();
  };

  const handleClose = () => {
    setScannedBarcode(null);
    setManualBarcode("");
    onClose();
  };

  return (
    <Modal opened={opened} onClose={handleClose} title="Scan Equipment" size="md">
      <Stack gap="md">
        <BarcodeScanner onDetected={(code) => setScannedBarcode(code)} />

        <TextInput
          label="Or enter barcode manually"
          placeholder="Type barcode..."
          value={manualBarcode}
          onChange={(e) => {
            setManualBarcode(e.currentTarget.value);
            setScannedBarcode(null);
          }}
        />

        {barcode && !matchedItem && (
          <Alert color="yellow" variant="light">
            No equipment found with barcode: <strong>{barcode}</strong>. Register it first.
          </Alert>
        )}

        {matchedItem && (
          <Stack gap="xs">
            <Text fw={600}>{matchedItem.name}</Text>
            <Group gap="xs">
              <Badge variant="light">{matchedItem.type}</Badge>
              <Badge color={matchedItem.status === "available" ? "teal" : "orange"}>
                {matchedItem.status.replace("_", " ")}
              </Badge>
            </Group>

            <Group gap="sm" mt="sm">
              {matchedItem.status === "checked_out" ? (
                <Button
                  leftSection={<IconLogin size={16} />}
                  color="teal"
                  onClick={() => handleAction("check_in")}
                >
                  Check In
                </Button>
              ) : (
                <Button
                  leftSection={<IconLogout size={16} />}
                  color="blue"
                  onClick={() => handleAction("check_out")}
                >
                  Check Out
                </Button>
              )}
            </Group>
          </Stack>
        )}
      </Stack>
    </Modal>
  );
}
