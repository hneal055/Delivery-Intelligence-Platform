import { Table, Badge, Title, Stack, Select, Group } from "@mantine/core";
import { useState, useMemo } from "react";
import { usePackages } from "../hooks/usePackages";

function statusColor(status: string): string {
  switch (status) {
    case "delivered": return "teal";
    case "pending": return "orange";
    case "exception": return "red";
    case "loaded": return "blue";
    default: return "gray";
  }
}

export function PackagesPage() {
  const { data: packages = [], isLoading } = usePackages();
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

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
            { value: "loaded", label: "Loaded" },
            { value: "delivered", label: "Delivered" },
            { value: "exception", label: "Exception" },
          ]}
        />
      </Group>

      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Package ID</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Driver</Table.Th>
            <Table.Th>Destination</Table.Th>
            <Table.Th>ETA (sec)</Table.Th>
            <Table.Th>Created</Table.Th>
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
                <code>{pkg.id.length > 16 ? `${pkg.id.slice(0, 16)}...` : pkg.id}</code>
              </Table.Td>
              <Table.Td>
                <Badge color={statusColor(pkg.status)} size="sm">
                  {pkg.status}
                </Badge>
              </Table.Td>
              <Table.Td>
                {pkg.driver_id ? (
                  <code>{pkg.driver_id.slice(0, 12)}...</code>
                ) : (
                  <span style={{ color: "#999" }}>Unassigned</span>
                )}
              </Table.Td>
              <Table.Td>
                {pkg.dest_address || `${pkg.dest_lat.toFixed(4)}, ${pkg.dest_lon.toFixed(4)}`}
              </Table.Td>
              <Table.Td>
                {pkg.predicted_eta_seconds
                  ? `${Math.round(pkg.predicted_eta_seconds)}s`
                  : "N/A"}
              </Table.Td>
              <Table.Td>
                {pkg.created_at
                  ? new Date(pkg.created_at).toLocaleString()
                  : "N/A"}
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
