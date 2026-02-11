import { Modal, TextInput, Button, Group, Textarea, Select } from '@mantine/core';
import { DateTimePicker } from '@mantine/dates';
import { useForm } from '@mantine/form';
import { useDispatch } from '../../hooks/useDispatch';

interface CreateJobModalProps {
  opened: boolean;
  onClose: () => void;
}

export function CreateJobModal({ opened, onClose }: CreateJobModalProps) {
  const { createJob } = useDispatch();

  const form = useForm({
    initialValues: {
      title: '',
      notes: '',
      type: 'delivery',
      priority: 'medium',
      scheduled_at: new Date(),
    },
    validate: {
      title: (value) => (value.length < 2 ? 'Title must be at least 2 characters' : null),
      scheduled_at: (value) => (value ? null : 'Scheduled time is required'),
    },
  });

  const handleSubmit = (values: typeof form.values) => {
    createJob.mutate({
      title: values.title,
      notes: values.notes || undefined,
      type: values.type,
      priority: values.priority,
      scheduled_at: values.scheduled_at.toISOString(),
    }, {
      onSuccess: () => {
        form.reset();
        onClose();
      }
    });
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Create New Dispatch Job">
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <TextInput
          withAsterisk
          label="Job Title"
          placeholder="e.g. Morning Delivery Route A"
          {...form.getInputProps('title')}
          mb="sm"
        />

        <Group grow mb="sm">
          <Select
            label="Type"
            data={[
              { value: 'delivery', label: 'Delivery' },
              { value: 'pickup', label: 'Pickup' },
              { value: 'service', label: 'Service' },
            ]}
            {...form.getInputProps('type')}
          />
          <Select
            label="Priority"
            data={[
              { value: 'low', label: 'Low' },
              { value: 'medium', label: 'Medium' },
              { value: 'high', label: 'High' },
              { value: 'urgent', label: 'Urgent' },
            ]}
            {...form.getInputProps('priority')}
          />
        </Group>

        <DateTimePicker
          withAsterisk
          label="Scheduled Time"
          placeholder="Pick date and time"
          {...form.getInputProps('scheduled_at')}
          mb="sm"
        />

        <Textarea
          label="Notes"
          placeholder="Optional details..."
          {...form.getInputProps('notes')}
          mb="md"
        />

        <Group justify="flex-end">
          <Button variant="subtle" onClick={onClose}>Cancel</Button>
          <Button type="submit" loading={createJob.isPending}>Create Job</Button>
        </Group>
      </form>
    </Modal>
  );
}
