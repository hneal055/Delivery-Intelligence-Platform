import { useState } from "react";
import { Title, Container, Button, Group, Stack, SimpleGrid, Paper, Text, Badge, Timeline } from "@mantine/core";
import { IconPlus, IconScan, IconLogin, IconLogout } from "@tabler/icons-react";
import { useEquipmentStore } from "../stores/equipmentStore";
import { useAuthStore } from "../stores/authStore";
import { EquipmentTable } from "../components/equipment/EquipmentTable";
import { AddEquipmentModal } from "../components/equipment/AddEquipmentModal";
import { EquipmentCheckModal } from "../components/equipment/EquipmentCheckModal";

export function EquipmentPage() {
  const equipment = useEquipmentStore((s) => s.equipment);
  const scanEvents = useEquipmentStore((s) => s.scanEvents);
  const checkIn = useEquipmentStore((s) => s.checkIn);
  const checkOut = useEquipmentStore((s) => s.checkOut);
  const removeEquipment = useEquipmentStore((s) => s.removeEquipment);
  const user = useAuthStore((s) => s.user);

  const [addModalOpen, setAddModalOpen] = useState(false);
  const [scanModalOpen, setScanModalOpen] = useState(false);

  const totalCount = equipment.length;
  const availableCount = equipment.filter((e) => e.status === "available").length;
  const checkedOutCount = equipment.filter((e) => e.status === "checked_out").length;

  const handleCheckOut = (id: string) => {
    checkOut(id, user?.username ?? "unknown");
  };

  const handleDelete = (id: string) => {
    if (confirm("Remove this equipment?")) {
      removeEquipment(id);
    }
  };

  return (
    <Container size="xl" py="xl">
      <Stack gap="md">
        <Group justify="space-between">
          <Title order={2}>Equipment Management</Title>
          <Group gap="sm">
            <Button variant="light" leftSection={<IconScan size={18} />} onClick={() => setScanModalOpen(true)}>
              Scan
            </Button>
            <Button leftSection={<IconPlus size={18} />} onClick={() => setAddModalOpen(true)}>
              Add Equipment
            </Button>
          </Group>
        </Group>

        <SimpleGrid cols={{ base: 1, sm: 3 }}>
          <Paper p="md" radius="md" withBorder>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Total</Text>
            <Text size="xl" fw={700}>{totalCount}</Text>
          </Paper>
          <Paper p="md" radius="md" withBorder>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Available</Text>
            <Text size="xl" fw={700} c="teal">{availableCount}</Text>
          </Paper>
          <Paper p="md" radius="md" withBorder>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>Checked Out</Text>
            <Text size="xl" fw={700} c="orange">{checkedOutCount}</Text>
          </Paper>
        </SimpleGrid>

        <EquipmentTable
          equipment={equipment}
          onCheckIn={checkIn}
          onCheckOut={handleCheckOut}
          onDelete={handleDelete}
        />

        {scanEvents.length > 0 && (
          <Paper p="md" radius="md" withBorder>
            <Text fw={600} mb="sm">Recent Activity</Text>
            <Timeline active={-1} bulletSize={20} lineWidth={2}>
              {scanEvents.slice(0, 10).map((event, i) => (
                <Timeline.Item
                  key={i}
                  bullet={event.action === "check_in" ? <IconLogin size={12} /> : <IconLogout size={12} />}
                  title={
                    <Group gap="xs">
                      <Text size="sm" fw={500}>{event.action === "check_in" ? "Checked In" : "Checked Out"}</Text>
                      <Badge size="xs" variant="light">{event.barcode}</Badge>
                    </Group>
                  }
                >
                  <Text size="xs" c="dimmed">
                    by {event.driver_id} at {new Date(event.timestamp).toLocaleString()}
                  </Text>
                </Timeline.Item>
              ))}
            </Timeline>
          </Paper>
        )}
      </Stack>

      <AddEquipmentModal
        opened={addModalOpen}
        onClose={() => setAddModalOpen(false)}
      />

      <EquipmentCheckModal
        opened={scanModalOpen}
        onClose={() => setScanModalOpen(false)}
        driverId={user?.username ?? "unknown"}
      />
    </Container>
  );
}
