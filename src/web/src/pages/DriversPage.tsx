import { Table, Badge, Title, Stack, TextInput, Select, Group } from "@mantine/core";
import { useState, useMemo } from "react";
import { useDrivers } from "../hooks/useDrivers";

export function DriversPage() {
  const { data: drivers = [], isLoading } = useDrivers();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return drivers.filter((d) => {
      const matchesSearch = !search || d.name.toLowerCase().includes(search.toLowerCase()) || d.id.toLowerCase().includes(search.toLowerCase());
      const matchesStatus = !statusFilter || d.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [drivers, search, statusFilter]);

  return (
    <Stack>
      <Title order={3}>Drivers</Title>

      <Group>
        <TextInput
          placeholder="Search by name or ID..."
          value={search}
          onChange={(e) => setSearch(e.currentTarget.value)}
          style={{ flex: 1, maxWidth: 300 }}
        />
        <Select
          placeholder="Filter by status"
          clearable
          value={statusFilter}
          onChange={setStatusFilter}
          data={[
            { value: "active", label: "Active" },
            { value: "inactive", label: "Inactive" },
          ]}
        />
      </Group>

      <Table striped highlightOnHover>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Name</Table.Th>
            <Table.Th>Status</Table.Th>
            <Table.Th>Online</Table.Th>
            <Table.Th>Packages</Table.Th>
            <Table.Th>Location</Table.Th>
            <Table.Th>Last Updated</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {isLoading && (
            <Table.Tr>
              <Table.Td colSpan={6}>Loading...</Table.Td>
            </Table.Tr>
          )}
          {filtered.map((driver) => (
            <Table.Tr key={driver.id}>
              <Table.Td fw={500}>{driver.name}</Table.Td>
              <Table.Td>
                <Badge color={driver.status === "active" ? "blue" : "gray"} size="sm">
                  {driver.status}
                </Badge>
              </Table.Td>
              <Table.Td>
                <Badge color={driver.is_online ? "green" : "gray"} variant="dot" size="sm">
                  {driver.is_online ? "Online" : "Offline"}
                </Badge>
              </Table.Td>
              <Table.Td>{driver.package_count}</Table.Td>
              <Table.Td>
                {driver.current_lat && driver.current_lon ? (
                  <code>{driver.current_lat.toFixed(4)}, {driver.current_lon.toFixed(4)}</code>
                ) : (
                  <span style={{ color: "#999" }}>N/A</span>
                )}
              </Table.Td>
              <Table.Td>
                {driver.last_updated
                  ? new Date(driver.last_updated).toLocaleString()
                  : "Never"}
              </Table.Td>
            </Table.Tr>
          ))}
          {filtered.length === 0 && !isLoading && (
            <Table.Tr>
              <Table.Td colSpan={6} ta="center" c="dimmed">
                No drivers found
              </Table.Td>
            </Table.Tr>
          )}
        </Table.Tbody>
      </Table>
    </Stack>
  );
}
