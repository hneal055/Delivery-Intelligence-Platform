import { useState } from "react";
import { Grid, Stack, ScrollArea, Title, Text } from "@mantine/core";
import { DashboardStats } from "../components/dispatch/DashboardStats";
import { DispatchMap } from "../components/map/DispatchMap";
import { DriverCard } from "../components/dispatch/DriverCard";
import { useDrivers } from "../hooks/useDrivers";
import { useDashboardSummary } from "../hooks/useDashboardSummary";
import { useWebSocket } from "../hooks/useWebSocket";

export function DashboardPage() {
  const { data: drivers = [], isLoading: driversLoading } = useDrivers();
  const { data: summary, isLoading: summaryLoading } = useDashboardSummary();
  const [selectedDriverId, setSelectedDriverId] = useState<string | null>(null);

  // Connect WebSocket for real-time updates
  useWebSocket();

  return (
    <Stack gap="md" h="calc(100vh - 100px)">
      <DashboardStats summary={summary} isLoading={summaryLoading} />

      <Grid gutter="md" style={{ flex: 1 }}>
        <Grid.Col span={8}>
          <div style={{ height: "100%", minHeight: "400px" }}>
            <DispatchMap
              drivers={drivers}
              selectedDriverId={selectedDriverId}
              onSelectDriver={setSelectedDriverId}
            />
          </div>
        </Grid.Col>

        <Grid.Col span={4}>
          <Stack gap="xs">
            <Title order={5}>
              Drivers ({drivers.length})
            </Title>
            {driversLoading && <Text size="sm" c="dimmed">Loading drivers...</Text>}
            <ScrollArea h="calc(100vh - 320px)">
              <Stack gap="xs">
                {drivers.map((driver) => (
                  <DriverCard
                    key={driver.id}
                    driver={driver}
                    isSelected={driver.id === selectedDriverId}
                    onClick={() =>
                      setSelectedDriverId(
                        driver.id === selectedDriverId ? null : driver.id
                      )
                    }
                  />
                ))}
                {drivers.length === 0 && !driversLoading && (
                  <Text size="sm" c="dimmed" ta="center">
                    No drivers found. Start the fleet simulator to see data.
                  </Text>
                )}
              </Stack>
            </ScrollArea>
          </Stack>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
