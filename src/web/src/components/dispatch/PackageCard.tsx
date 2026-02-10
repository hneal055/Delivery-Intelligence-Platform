import { Paper, Text, Badge, Group } from "@mantine/core";
import type { Package } from "../../types";

interface PackageCardProps {
  pkg: Package;
}

function statusColor(status: string): string {
  switch (status) {
    case "delivered": return "teal";
    case "pending": return "orange";
    case "exception": return "red";
    case "loaded": return "blue";
    default: return "gray";
  }
}

export function PackageCard({ pkg }: PackageCardProps) {
  return (
    <Paper withBorder p="sm" radius="md">
      <Group justify="space-between" mb={4}>
        <Text fw={600} size="sm" ff="monospace">{pkg.id.slice(0, 12)}...</Text>
        <Badge size="sm" color={statusColor(pkg.status)}>
          {pkg.status}
        </Badge>
      </Group>
      <Text size="xs" c="dimmed">
        {pkg.dest_address || `${pkg.dest_lat.toFixed(4)}, ${pkg.dest_lon.toFixed(4)}`}
      </Text>
      {pkg.driver_id && (
        <Text size="xs" c="dimmed">Driver: {pkg.driver_id.slice(0, 12)}...</Text>
      )}
    </Paper>
  );
}
