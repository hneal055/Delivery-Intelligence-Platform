import { Group, TextInput, Select } from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";

interface ProofFilterBarProps {
  search: string;
  onSearchChange: (value: string) => void;
  dateRange: string | null;
  onDateRangeChange: (value: string | null) => void;
}

export function ProofFilterBar({
  search,
  onSearchChange,
  dateRange,
  onDateRangeChange,
}: ProofFilterBarProps) {
  return (
    <Group gap="md">
      <TextInput
        placeholder="Search by package or driver ID..."
        leftSection={<IconSearch size={16} />}
        value={search}
        onChange={(e) => onSearchChange(e.currentTarget.value)}
        style={{ flex: 1, minWidth: 200 }}
      />
      <Select
        placeholder="Time range"
        value={dateRange}
        onChange={onDateRangeChange}
        data={[
          { value: "today", label: "Today" },
          { value: "7days", label: "Last 7 days" },
          { value: "30days", label: "Last 30 days" },
          { value: "all", label: "All time" },
        ]}
        clearable
        w={160}
      />
    </Group>
  );
}
