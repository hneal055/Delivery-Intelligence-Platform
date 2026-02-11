import { Modal, Select, Button, Group, Text, Badge } from '@mantine/core';
import { useForm } from '@mantine/form';
import { useDispatch } from '../../hooks/useDispatch';
import { useDrivers } from '../../hooks/useDrivers';
import type { DispatchJob } from '../../types';

interface AssignmentModalProps {
  job: DispatchJob | null;
  opened: boolean;
  onClose: () => void;
}

export function AssignmentModal({ job, opened, onClose }: AssignmentModalProps) {
  const { assignJob } = useDispatch();
  const { data: drivers } = useDrivers();

  const form = useForm({
    initialValues: {
      driverId: '',
    },
    validate: {
      driverId: (value) => (value ? null : 'Please select a driver'),
    },
  });

  const handleSubmit = (values: typeof form.values) => {
    if (!job) return;
    assignJob.mutate({
      jobId: job.id,
      driverId: values.driverId,
    }, {
      onSuccess: () => {
        form.reset();
        onClose();
      }
    });
  };

  // Sort drivers: online first, then by lowest package count
  const sortedDrivers = [...(drivers ?? [])].sort((a, b) => {
    if (a.is_online !== b.is_online) return a.is_online ? -1 : 1;
    return a.package_count - b.package_count;
  });

  const driverOptions = sortedDrivers.map(d => ({
    value: d.id,
    label: `${d.name} — ${d.package_count} pkgs (${d.is_online ? "Online" : "Offline"})`,
  }));

  return (
    <Modal opened={opened} onClose={onClose} title={`Assign Driver to: ${job?.title}`}>
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Group gap="xs" mb="md">
          <Text size="sm" c="dimmed">Job type:</Text>
          <Badge variant="light" size="sm">{job?.type}</Badge>
          <Text size="sm" c="dimmed">Priority:</Text>
          <Badge variant="outline" size="sm">{job?.priority}</Badge>
        </Group>

        <Select
          withAsterisk
          label="Select Driver"
          placeholder="Choose a driver"
          data={driverOptions}
          {...form.getInputProps('driverId')}
          mb="md"
          searchable
        />

        <Group justify="flex-end">
          <Button variant="subtle" onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={assignJob.isPending}>Assign</Button>
        </Group>
      </form>
    </Modal>
  );
}
