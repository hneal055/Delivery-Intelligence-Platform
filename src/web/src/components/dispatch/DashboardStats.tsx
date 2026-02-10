import { SimpleGrid, Paper, Text, Group } from "@mantine/core";
import type { DashboardSummary } from "../../types";

interface DashboardStatsProps {
  summary: DashboardSummary | undefined;
  isLoading: boolean;
}

function StatCard({ label, value, color }: { label: string; value: number | string; color: string }) {
  return (
    <Paper withBorder p="md" radius="md">
      <Text size="xs" c="dimmed" tt="uppercase" fw={700}>
        {label}
      </Text>
      <Text fw={700} size="xl" c={color}>
        {value}
      </Text>
    </Paper>
  );
}

export function DashboardStats({ summary, isLoading }: DashboardStatsProps) {
  if (isLoading || !summary) {
    return (
      <SimpleGrid cols={{ base: 2, sm: 4 }}>
        {[1, 2, 3, 4].map((i) => (
          <Paper key={i} withBorder p="md" radius="md">
            <Text size="xs" c="dimmed">Loading...</Text>
          </Paper>
        ))}
      </SimpleGrid>
    );
  }

  return (
    <SimpleGrid cols={{ base: 2, sm: 4 }}>
      <StatCard label="Online Drivers" value={summary.online_drivers} color="green" />
      <StatCard label="Active Drivers" value={summary.active_drivers} color="blue" />
      <StatCard label="Pending Packages" value={summary.pending_packages} color="orange" />
      <StatCard label="Delivered" value={summary.delivered_packages} color="teal" />
      <StatCard label="Total Drivers" value={summary.total_drivers} color="gray" />
      <StatCard label="Total Packages" value={summary.total_packages} color="gray" />
      <StatCard label="Exceptions" value={summary.exception_packages} color="red" />
    </SimpleGrid>
  );
}
