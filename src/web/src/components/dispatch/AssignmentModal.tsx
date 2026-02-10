import { Modal, Select, Button, Group, Text } from '@mantine/core';
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

  const driverOptions = drivers?.map(d => ({
    value: d.id,
    label: `${d.name} (${d.status})`
  })) || [];

  return (
    <Modal opened={opened} onClose={onClose} title={`Assign Driver to: ${job?.title}`}>
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Text size="sm" mb="md" c="dimmed">
          Job requires: {job?.estimated_duration_minutes} minutes.
        </Text>

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
