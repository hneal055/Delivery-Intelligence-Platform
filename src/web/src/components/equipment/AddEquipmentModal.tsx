import { Modal, TextInput, Select, Textarea, Button, Group } from "@mantine/core";
import { useForm } from "@mantine/form";
import { useEquipmentStore } from "../../stores/equipmentStore";

interface AddEquipmentModalProps {
  opened: boolean;
  onClose: () => void;
  prefillBarcode?: string | null;
}

export function AddEquipmentModal({ opened, onClose, prefillBarcode }: AddEquipmentModalProps) {
  const addEquipment = useEquipmentStore((s) => s.addEquipment);

  const form = useForm({
    initialValues: {
      name: "",
      barcode: prefillBarcode ?? "",
      type: "scanner",
      notes: "",
    },
    validate: {
      name: (v) => (v.length < 1 ? "Name is required" : null),
      barcode: (v) => (v.length < 1 ? "Barcode is required" : null),
    },
  });

  const handleSubmit = (values: typeof form.values) => {
    addEquipment({
      id: crypto.randomUUID(),
      barcode: values.barcode,
      name: values.name,
      type: values.type,
      status: "available",
      checked_out_by: null,
      checked_out_at: null,
      notes: values.notes || null,
    });
    form.reset();
    onClose();
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Add Equipment">
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <TextInput
          withAsterisk
          label="Name"
          placeholder="e.g. Handheld Scanner #4"
          {...form.getInputProps("name")}
          mb="sm"
        />

        <TextInput
          withAsterisk
          label="Barcode"
          placeholder="Scan or type barcode"
          {...form.getInputProps("barcode")}
          mb="sm"
        />

        <Select
          label="Type"
          data={[
            { value: "scanner", label: "Scanner" },
            { value: "dolly", label: "Dolly" },
            { value: "radio", label: "Radio" },
            { value: "vehicle_key", label: "Vehicle Key" },
            { value: "other", label: "Other" },
          ]}
          {...form.getInputProps("type")}
          mb="sm"
        />

        <Textarea
          label="Notes"
          placeholder="Optional notes..."
          {...form.getInputProps("notes")}
          mb="md"
        />

        <Group justify="flex-end">
          <Button variant="subtle" onClick={onClose}>Cancel</Button>
          <Button type="submit">Add Equipment</Button>
        </Group>
      </form>
    </Modal>
  );
}
