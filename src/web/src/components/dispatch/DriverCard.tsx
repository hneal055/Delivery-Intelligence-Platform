import { Paper, Text, Badge, Group, Stack, Button } from "@mantine/core";
import type { Driver } from "../../types";

interface DriverCardProps {
  driver: Driver;
  isSelected?: boolean;
  onClick?: () => void;
  /** Shown on the selected card: open Packages filtered to this driver. */
  onViewPackages?: () => void;
}

export function DriverCard({ driver, isSelected, onClick, onViewPackages }: DriverCardProps) {
  return (
    <Paper
      withBorder
      p="sm"
      radius="md"
      onClick={onClick}
      style={{
        cursor: onClick ? "pointer" : "default",
        borderColor: isSelected ? "var(--mantine-color-blue-5)" : undefined,
        backgroundColor: isSelected ? "var(--mantine-color-blue-0)" : undefined,
      }}
    >
      <Group justify="space-between" mb={4}>
        <Text fw={600} size="sm">{driver.name}</Text>
        <Badge
          size="sm"
          color={driver.is_online ? "green" : "gray"}
          variant="dot"
        >
          {driver.is_online ? "Online" : "Offline"}
        </Badge>
      </Group>
      <Stack gap={2}>
        <Text size="xs" c="dimmed">
          Status: {driver.status} | Packages: {driver.package_count}
        </Text>
        {driver.current_lat && driver.current_lon && (
          <Text size="xs" c="dimmed" ff="monospace">
            {driver.current_lat.toFixed(4)}, {driver.current_lon.toFixed(4)}
          </Text>
        )}
        {isSelected && onViewPackages && (
          <Button
            size="xs"
            variant="light"
            mt={6}
            onClick={(e) => {
              e.stopPropagation(); // keep the card selected
              onViewPackages();
            }}
          >
            View packages ({driver.package_count}) →
          </Button>
        )}
      </Stack>
    </Paper>
  );
}
