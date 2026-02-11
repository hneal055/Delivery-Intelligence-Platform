import { Table, Badge, ActionIcon, Text, Menu } from "@mantine/core";
import { IconDotsVertical, IconLogin, IconLogout, IconTrash } from "@tabler/icons-react";
import type { Equipment } from "../../types";

interface EquipmentTableProps {
  equipment: Equipment[];
  onCheckIn: (id: string) => void;
  onCheckOut: (id: string) => void;
  onDelete: (id: string) => void;
}

const statusColors: Record<string, string> = {
  available: "teal",
  checked_out: "orange",
  maintenance: "red",
};

export function EquipmentTable({ equipment, onCheckIn, onCheckOut, onDelete }: EquipmentTableProps) {
  if (equipment.length === 0) {
    return (
      <Text c="dimmed" ta="center" py="xl">
        No equipment registered. Add some to get started.
      </Text>
    );
  }

  return (
    <Table striped highlightOnHover withTableBorder>
      <Table.Thead>
        <Table.Tr>
          <Table.Th>Name</Table.Th>
          <Table.Th>Barcode</Table.Th>
          <Table.Th>Type</Table.Th>
          <Table.Th>Status</Table.Th>
          <Table.Th>Checked Out By</Table.Th>
          <Table.Th>Actions</Table.Th>
        </Table.Tr>
      </Table.Thead>
      <Table.Tbody>
        {equipment.map((item) => (
          <Table.Tr key={item.id}>
            <Table.Td>{item.name}</Table.Td>
            <Table.Td>
              <Text size="sm" ff="monospace">{item.barcode}</Text>
            </Table.Td>
            <Table.Td>
              <Badge variant="light" size="sm">{item.type}</Badge>
            </Table.Td>
            <Table.Td>
              <Badge color={statusColors[item.status] ?? "gray"} size="sm">
                {item.status.replace("_", " ")}
              </Badge>
            </Table.Td>
            <Table.Td>
              {item.checked_out_by ? (
                <Text size="sm">{item.checked_out_by}</Text>
              ) : (
                <Text size="sm" c="dimmed">—</Text>
              )}
            </Table.Td>
            <Table.Td>
              <Menu shadow="md" width={180}>
                <Menu.Target>
                  <ActionIcon variant="subtle" color="gray">
                    <IconDotsVertical size={16} />
                  </ActionIcon>
                </Menu.Target>
                <Menu.Dropdown>
                  {item.status === "checked_out" ? (
                    <Menu.Item leftSection={<IconLogin size={14} />} onClick={() => onCheckIn(item.id)}>
                      Check In
                    </Menu.Item>
                  ) : (
                    <Menu.Item leftSection={<IconLogout size={14} />} onClick={() => onCheckOut(item.id)}>
                      Check Out
                    </Menu.Item>
                  )}
                  <Menu.Divider />
                  <Menu.Item color="red" leftSection={<IconTrash size={14} />} onClick={() => onDelete(item.id)}>
                    Remove
                  </Menu.Item>
                </Menu.Dropdown>
              </Menu>
            </Table.Td>
          </Table.Tr>
        ))}
      </Table.Tbody>
    </Table>
  );
}
