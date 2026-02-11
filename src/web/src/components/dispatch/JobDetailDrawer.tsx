import { Drawer, Stack, Text, Badge, Group, Button, Divider } from "@mantine/core";
import { IconPlayerPlay, IconCheck, IconX, IconUserPlus } from "@tabler/icons-react";
import { useJobDetail } from "../../hooks/useJobDetail";
import { useDispatch } from "../../hooks/useDispatch";
import { useDrivers } from "../../hooks/useDrivers";

interface JobDetailDrawerProps {
  jobId: string | null;
  opened: boolean;
  onClose: () => void;
  onAssign: () => void;
}

const statusColors: Record<string, string> = {
  pending: "orange",
  assigned: "blue",
  in_progress: "cyan",
  completed: "teal",
  cancelled: "red",
};

const priorityColors: Record<string, string> = {
  low: "gray",
  medium: "blue",
  high: "orange",
  urgent: "red",
};

export function JobDetailDrawer({ jobId, opened, onClose, onAssign }: JobDetailDrawerProps) {
  const { data: job, isLoading } = useJobDetail(jobId);
  const { updateJobStatus } = useDispatch();
  const { data: drivers = [] } = useDrivers();

  const assignedDriver = job?.driver_id
    ? drivers.find((d) => d.id === job.driver_id)
    : null;

  const handleStatusChange = (status: string) => {
    if (!job) return;
    updateJobStatus.mutate({ jobId: job.id, status });
  };

  return (
    <Drawer opened={opened} onClose={onClose} title="Job Details" position="right" size="md">
      {isLoading || !job ? (
        <Text c="dimmed">Loading...</Text>
      ) : (
        <Stack gap="md">
          <Text fw={700} size="lg">{job.title}</Text>

          <Group gap="xs">
            <Badge color={statusColors[job.status] ?? "gray"} size="lg">
              {job.status}
            </Badge>
            <Badge color={priorityColors[job.priority] ?? "gray"} variant="outline" size="lg">
              {job.priority}
            </Badge>
            <Badge color="gray" variant="light" size="lg">
              {job.type}
            </Badge>
          </Group>

          <Divider />

          <Stack gap="xs">
            <Text size="sm" fw={500}>Scheduled</Text>
            <Text size="sm" c="dimmed">
              {job.scheduled_at ? new Date(job.scheduled_at).toLocaleString() : "Not scheduled"}
            </Text>
          </Stack>

          {job.completed_at && (
            <Stack gap="xs">
              <Text size="sm" fw={500}>Completed</Text>
              <Text size="sm" c="dimmed">{new Date(job.completed_at).toLocaleString()}</Text>
            </Stack>
          )}

          <Stack gap="xs">
            <Text size="sm" fw={500}>Assigned Driver</Text>
            {assignedDriver ? (
              <Group gap="xs">
                <Text size="sm">{assignedDriver.name}</Text>
                <Badge size="xs" color={assignedDriver.is_online ? "green" : "gray"}>
                  {assignedDriver.is_online ? "Online" : "Offline"}
                </Badge>
              </Group>
            ) : (
              <Text size="sm" c="dimmed">Unassigned</Text>
            )}
          </Stack>

          {job.notes && (
            <Stack gap="xs">
              <Text size="sm" fw={500}>Notes</Text>
              <Text size="sm" c="dimmed">{job.notes}</Text>
            </Stack>
          )}

          <Stack gap="xs">
            <Text size="sm" fw={500}>Created</Text>
            <Text size="sm" c="dimmed">{new Date(job.created_at).toLocaleString()}</Text>
          </Stack>

          <Divider />

          <Text size="sm" fw={500}>Actions</Text>
          <Group gap="xs">
            {!job.driver_id && (
              <Button
                size="xs"
                variant="light"
                leftSection={<IconUserPlus size={14} />}
                onClick={onAssign}
              >
                Assign
              </Button>
            )}
            {job.status === "pending" || job.status === "assigned" ? (
              <Button
                size="xs"
                variant="light"
                color="cyan"
                leftSection={<IconPlayerPlay size={14} />}
                onClick={() => handleStatusChange("in_progress")}
              >
                Start
              </Button>
            ) : null}
            {job.status === "in_progress" && (
              <Button
                size="xs"
                variant="light"
                color="teal"
                leftSection={<IconCheck size={14} />}
                onClick={() => handleStatusChange("completed")}
              >
                Complete
              </Button>
            )}
            {job.status !== "cancelled" && job.status !== "completed" && (
              <Button
                size="xs"
                variant="light"
                color="red"
                leftSection={<IconX size={14} />}
                onClick={() => handleStatusChange("cancelled")}
              >
                Cancel
              </Button>
            )}
          </Group>
        </Stack>
      )}
    </Drawer>
  );
}
