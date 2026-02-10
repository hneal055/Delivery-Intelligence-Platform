import { Modal, TextInput, NumberInput, Button, Group, Textarea } from '@mantine/core';
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
      description: '',
      scheduled_time: new Date(),
      estimated_duration_minutes: 60,
    },
    validate: {
      title: (value) => (value.length < 2 ? 'Title must be at least 2 characters' : null),
      scheduled_time: (value) => (value ? null : 'Scheduled time is required'),
      estimated_duration_minutes: (value) => (value > 0 ? null : 'Duration must be positive'),
    },
  });

  const handleSubmit = (values: typeof form.values) => {
    createJob.mutate({
      title: values.title,
      description: values.description,
      scheduled_time: values.scheduled_time.toISOString(),
      estimated_duration_minutes: values.estimated_duration_minutes,
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
        
        <Textarea
          label="Description"
          placeholder="Optional details..."
          {...form.getInputProps('description')}
          mb="sm"
        />

        <DateTimePicker
          withAsterisk
          label="Scheduled Time"
          placeholder="Pick date and time"
          {...form.getInputProps('scheduled_time')}
          mb="sm"
        />

        <NumberInput
          withAsterisk
          label="Estimated Duration (minutes)"
          min={1}
          {...form.getInputProps('estimated_duration_minutes')}
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
