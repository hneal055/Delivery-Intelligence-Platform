import { Table, Badge, Title, Stack, Select, Group, Button, Text } from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useMemo } from "react";
import { usePackages } from "../hooks/usePackages";
import { markPackageReady, reopenPackage } from "../api/dispatch";
import type { Package } from "../types";

function statusColor(status: string): string {
  switch (status) {
    case "delivered": return "teal";
    case "pending": return "orange";
    case "assigned": return "yellow";
    case "exception": return "red";
    case "loaded": return "blue";
    default: return "gray";
  }
}

// A package waiting at its pickup point that the shipper has not released yet
function awaitingReady(pkg: Package): boolean {
  return Boolean(pkg.pickup_address) && !pkg.ready_at &&
    (pkg.status === "pending" || pkg.status === "assigned");
}

export function PackagesPage() {
  const { data: packages = [], isLoading } = usePackages();
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const onDone = (title: string) => () => {
    notifications.show({ color: "teal", title, message: "The driver has been alerted." });
    queryClient.invalidateQueries({ queryKey: ["packages"] });
  };
  const onError = (err: unknown) => {
    const detail = (err as { response?: { data?: { detail?: string } } }).response?.data?.detail;
    notifications.show({ color: "red", title: "Could not update package", message: detail ?? "Try again." });
  };
  const ready = useMutation({ mutationFn: markPackageReady, onSuccess: onDone("Marked ready for pickup"), onError });
  const reopen = useMutation({ mutationFn: reopenPackage, onSuccess: onDone("Package reopened"), onError });

  const filtered = useMemo(() => {
    if (!statusFilter) return packages;
    return packages.filter((p) => p.status === statusFilter);
  }, [packages, statusFilter]);

  return (
    <Stack>
      <Title order={3}>Packages</Title>

      <Group>
        <Select
          placeholder="Filter by status"
          clearable
          value={statusFilter}
          onChange={setStatusFilter}
          data={[
            { value: "pending", label: "Pending" },
            { value: "assigned", label: "Assigned" },
            { value: "loaded", label: "Picked up" },
            { value: "delivered", label: "Delivered" },
            { value: "exception", label: "Problem reported" },
          ]}
        />
      </Group>

      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Tracking</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Driver</Table.Th>
            <Table.Th>Pickup → Delivery</Table.Th>
            <Table.Th>Created</Table.Th>
            <Table.Th>Actions</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {isLoading && (
            <Table.Tr>
              <Table.Td colSpan={6}>Loading...</Table.Td>
            </Table.Tr>
          )}
          {filtered.map((pkg) => (
            <Table.Tr key={pkg.id}>
              <Table.Td>
                <code>{pkg.tracking_code ?? (pkg.id.length > 16 ? `${pkg.id.slice(0, 16)}...` : pkg.id)}</code>
              </Table.Td>
              <Table.Td>
                <Badge color={statusColor(pkg.status)} size="sm">
                  {pkg.status === "exception" ? "problem" : pkg.status === "loaded" ? "picked up" : pkg.status}
                </Badge>
                {awaitingReady(pkg) && (
                  <Text size="xs" c="orange">Not ready for pickup</Text>
                )}
                {pkg.status === "exception" && pkg.exception_reason && (
                  <Text size="xs" c="red">{pkg.exception_reason}</Text>
                )}
              </Table.Td>
              <Table.Td>
                {pkg.driver_id ?? <span style={{ color: "#999" }}>Unassigned</span>}
              </Table.Td>
              <Table.Td>
                {pkg.pickup_address && (
                  <Text size="sm" c="dimmed">From: {pkg.pickup_address}</Text>
                )}
                <Text size="sm">
                  {pkg.dest_address || `${pkg.dest_lat.toFixed(4)}, ${pkg.dest_lon.toFixed(4)}`}
                  {pkg.dest_unit ? ` — ${pkg.dest_unit}` : ""}
                </Text>
              </Table.Td>
              <Table.Td>
                {pkg.created_at ? new Date(pkg.created_at).toLocaleString() : "N/A"}
              </Table.Td>
              <Table.Td>
                {awaitingReady(pkg) && (
                  <Button size="xs" variant="light" loading={ready.isPending && ready.variables === pkg.id}
                    onClick={() => ready.mutate(pkg.id)}>
                    Mark ready
                  </Button>
                )}
                {pkg.status === "exception" && (
                  <Button size="xs" variant="light" color="red" loading={reopen.isPending && reopen.variables === pkg.id}
                    onClick={() => reopen.mutate(pkg.id)}>
                    Reopen
                  </Button>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
          {filtered.length === 0 && !isLoading && (
            <Table.Tr>
              <Table.Td colSpan={6} ta="center" c="dimmed">
                No packages found
              </Table.Td>
            </Table.Tr>
          )}
        </Table.Tbody>
      </Table>
    </Stack>
  );
}
