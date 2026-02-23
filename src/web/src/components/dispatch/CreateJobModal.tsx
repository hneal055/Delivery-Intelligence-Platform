import { Modal, TextInput, Button, Group, Textarea, Select, Stack } from '@mantine/core';
import { DateTimePicker } from '@mantine/dates';
import { useForm } from '@mantine/form';
import { useDispatch } from '../../hooks/useDispatch';
import { useDrivers } from '../../hooks/useDrivers';
import { JOB_TYPES } from '../../constants/dispatch';

interface CreateJobModalProps {
  opened: boolean;
  onClose: () => void;
}

const GRACE_MINUTES = 5;

function getLocalDayKey(date: Date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function CreateJobModal({ opened, onClose }: CreateJobModalProps) {
  const { createJob, useJobs } = useDispatch();
  const { data: jobs = [] } = useJobs();
  const { data: drivers } = useDrivers();
  const now = new Date();
  const minScheduledAt = new Date(Date.now() - GRACE_MINUTES * 60 * 1000);

  const form = useForm({
    initialValues: {
      title: '',
      notes: '',
      type: 'delivery',
      priority: 'low',
      scheduled_at: now,
      driver_id: '',
      package_id: '',
      status: 'pending',
    },
    validate: {
      title: (value, values) => {
        const trimmed = value.trim();
        if (trimmed.length < 2) return 'Title must be at least 2 characters';
        if (!values.scheduled_at) return null;

        const scheduledDay = getLocalDayKey(values.scheduled_at);
        const targetDriverId = values.driver_id || null;
        const duplicate = jobs.some((job) => {
          if (!job.scheduled_at) return false;
          const jobDay = getLocalDayKey(new Date(job.scheduled_at));
          const sameDay = jobDay === scheduledDay;
          const sameDriver = (job.driver_id || null) === targetDriverId;
          const sameTitle = job.title.trim().toLowerCase() === trimmed.toLowerCase();
          return sameDay && sameDriver && sameTitle;
        });

        return duplicate ? 'A job with this title already exists for that driver and day' : null;
      },
      type: (value) => (value ? null : 'Type is required'),
      scheduled_at: (value) => {
        if (!value) return 'Scheduled time is required';
        return value < minScheduledAt ? 'Scheduled time must be in the future' : null;
      },
      notes: (value, values) => {
        const hasNotes = value.trim().length > 0;
        if (values.priority === 'urgent' && !hasNotes) {
          return 'Notes are required for urgent jobs';
        }
        if (values.type === 'exception' && !hasNotes) {
          return 'Notes are required for exception jobs';
        }
        return null;
      },
      package_id: (value, values) => {
        if (values.type !== 'pickup') return null;
        const hasNotes = values.notes.trim().length > 0;
        const hasPackageId = value.trim().length > 0;
        return hasNotes || hasPackageId ? null : 'Pickup requires notes or package ID';
      },
    },
  });

  const driverOptions = (drivers ?? []).map((driver) => ({
    value: driver.id,
    label: `${driver.name} — ${driver.package_count} pkgs (${driver.is_online ? 'Online' : 'Offline'})`,
  }));

  const handleSubmit = (values: typeof form.values) => {
    createJob.mutate(
      {
        title: values.title.trim(),
        notes: values.notes.trim() || undefined,
        type: values.type,
        priority: values.priority,
        scheduled_at: values.scheduled_at.toISOString(),
        driver_id: values.driver_id || undefined,
        package_id: values.package_id.trim() || undefined,
      },
      {
        onSuccess: () => {
          form.reset();
          onClose();
        },
      }
    );
  };

  return (
    <Modal opened={opened} onClose={onClose} title="Create New Dispatch Job">
      <form onSubmit={form.onSubmit(handleSubmit)}>
        <Stack gap="sm">
          <TextInput
            withAsterisk
            label="Job Title"
            placeholder="e.g. Morning Delivery Route A"
            {...form.getInputProps('title')}
          />

          <Group grow>
            <Select
              label="Type"
              data={JOB_TYPES}
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
            minDate={now}
            {...form.getInputProps('scheduled_at')}
          />

          <Select
            label="Assign Driver (optional)"
            placeholder="Unassigned"
            data={driverOptions}
            searchable
            clearable
            {...form.getInputProps('driver_id')}
          />

          {form.values.type === 'pickup' && (
            <TextInput
              label="Package ID (optional)"
              placeholder="Enter package ID"
              {...form.getInputProps('package_id')}
            />
          )}

          <Textarea
            label="Notes"
            placeholder="Optional details..."
            {...form.getInputProps('notes')}
          />

          <TextInput
            label="Status"
            value="pending"
            disabled
          />

          <Group justify="flex-end">
            <Button variant="subtle" onClick={onClose}>Cancel</Button>
            <Button type="submit" loading={createJob.isPending} disabled={!form.isValid()}>
              Create Job
            </Button>
          </Group>
        </Stack>
      </form>
    </Modal>
  );
}
