import { Paper, Text, Badge, Stack, Group, SimpleGrid, Card } from "@mantine/core";
import type { DispatchJob } from "../../types";

interface SchedulingBoardProps {
  jobs: DispatchJob[];
  onJobClick: (job: DispatchJob) => void;
  onStatusChange?: (jobId: string, status: string) => void;
}

const columns = [
  { key: "pending", label: "Pending", color: "orange" },
  { key: "assigned", label: "Assigned", color: "blue" },
  { key: "in_progress", label: "In Progress", color: "cyan" },
  { key: "completed", label: "Completed", color: "teal" },
];

const priorityColors: Record<string, string> = {
  low: "gray",
  medium: "blue",
  high: "orange",
  urgent: "red",
};

export function SchedulingBoard({ jobs, onJobClick }: SchedulingBoardProps) {
  return (
    <SimpleGrid cols={4} spacing="md">
      {columns.map((col) => {
        const colJobs = jobs.filter((j) => j.status === col.key);
        return (
          <Paper key={col.key} p="sm" radius="md" withBorder style={{ minHeight: 300 }}>
            <Group justify="space-between" mb="sm">
              <Text fw={600} size="sm">{col.label}</Text>
              <Badge color={col.color} size="sm" variant="light">
                {colJobs.length}
              </Badge>
            </Group>

            <Stack gap="xs">
              {colJobs.length === 0 ? (
                <Text size="xs" c="dimmed" ta="center" py="lg">
                  No jobs
                </Text>
              ) : (
                colJobs.map((job) => (
                  <Card
                    key={job.id}
                    padding="xs"
                    radius="sm"
                    withBorder
                    onClick={() => onJobClick(job)}
                    style={{ cursor: "pointer" }}
                  >
                    <Text size="sm" fw={500} lineClamp={1}>{job.title}</Text>
                    <Group gap={4} mt={4}>
                      <Badge
                        size="xs"
                        color={priorityColors[job.priority] ?? "gray"}
                        variant="outline"
                      >
                        {job.priority}
                      </Badge>
                      <Badge size="xs" variant="light">{job.type}</Badge>
                    </Group>
                    {job.scheduled_at && (
                      <Text size="xs" c="dimmed" mt={4}>
                        {new Date(job.scheduled_at).toLocaleDateString()}
                      </Text>
                    )}
                    {job.driver_id && (
                      <Text size="xs" c="blue" mt={2}>
                        Assigned
                      </Text>
                    )}
                  </Card>
                ))
              )}
            </Stack>
          </Paper>
        );
      })}
    </SimpleGrid>
  );
}
