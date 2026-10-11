import { Modal, TextInput, Button, Group, Textarea, Select, Stack, Text, Checkbox } from '@mantine/core';
import { DateTimePicker } from '@mantine/dates';
import { useForm } from '@mantine/form';
import { useDispatch } from '../../hooks/useDispatch';
import { useDrivers } from '../../hooks/useDrivers';
import { JOB_TYPES } from '../../constants/dispatch';
import type { JobType } from '../../constants/dispatch';
import { useAddressPreview } from '../../hooks/useAddressPreview';
import type { AddressMatch } from '../../types';
import type { AddressStatus } from '../../hooks/useAddressPreview';

function MatchLine({ status, match }: { status: AddressStatus; match: AddressMatch | null }) {
  if (status === 'idle') return null;
  const color = status === 'found' ? (match?.used_default_area ? 'orange' : 'teal') : status === 'missing' ? 'red' : 'dimmed';
  return (
    <Text size="sm" c={color}>
      {status === 'checking' && 'Checking address…'}
      {status === 'missing' && 'No match yet. Add the city and state, or a ZIP code.'}
      {status === 'found' && match &&
        `Matched: ${match.matched_address}${match.used_default_area ? ' (Chicago assumed; add the city if this is a suburb)' : ''}`}
    </Text>
  );
}

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
      dest_address: '',
      dest_unit: '',
      delivery_instructions: '',
      pickup_address: '',
      pickup_instructions: '',
      ready_for_pickup: true,
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
      dest_address: (value, values) => {
        if (values.type !== 'delivery') return null;
        return value.trim().length >= 5 ? null : 'Delivery address is required';
      },
      package_id: (value, values) => {
        if (values.type !== 'pickup') return null;
        const hasNotes = values.notes.trim().length > 0;
        const hasPackageId = value.trim().length > 0;
        return hasNotes || hasPackageId ? null : 'Pickup requires notes or package ID';
      },
    },
  });

  // Live address check: show what the address matches before saving, so a
  // default-city guess is never saved unseen.
  const isDelivery = form.values.type === 'delivery';
  const { match: addressMatch, status: addressStatus } = useAddressPreview(form.values.dest_address, isDelivery);
  const hasPickup = isDelivery && form.values.pickup_address.trim().length > 0;
  const { match: pickupMatch, status: pickupStatus } = useAddressPreview(form.values.pickup_address, isDelivery);


  const driverOptions = (drivers ?? []).map((driver) => ({
    value: driver.id,
    label: `${driver.name} — ${driver.package_count} pkgs (${driver.is_online ? 'Online' : 'Offline'})`,
  }));

  const handleSubmit = (values: typeof form.values) => {
    createJob.mutate(
      {
        title: values.title.trim(),
        notes: values.notes.trim() || undefined,
        type: values.type as JobType,
        priority: values.priority,
        scheduled_at: values.scheduled_at.toISOString(),
        driver_id: values.driver_id || undefined,
        package_id: values.package_id.trim() || undefined,
        dest_address:
          values.type === 'delivery' ? values.dest_address.trim() || undefined : undefined,
        dest_unit:
          values.type === 'delivery' ? values.dest_unit.trim() || undefined : undefined,
        delivery_instructions:
          values.type === 'delivery' ? values.delivery_instructions.trim() || undefined : undefined,
        pickup_address:
          values.type === 'delivery' ? values.pickup_address.trim() || undefined : undefined,
        pickup_instructions:
          values.type === 'delivery' ? values.pickup_instructions.trim() || undefined : undefined,
        ready_for_pickup: values.ready_for_pickup,
      },
      {
        onSuccess: () => {
          form.reset();
          onClose();
        },
        onError: (err) => {
          // e.g. 422 "Address not found" from the geocoder
          const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
          form.setFieldError(
            values.type === 'delivery' ? 'dest_address' : 'title',
            typeof detail === 'string' ? detail : 'Could not create the job. Try again.'
          );
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

          {isDelivery && (
            <TextInput
              label="Pickup address (optional)"
              placeholder="Where the driver collects it; leave blank if it starts in the van"
              {...form.getInputProps('pickup_address')}
            />
          )}
          {isDelivery && <MatchLine status={pickupStatus} match={pickupMatch} />}
          {hasPickup && (
            <Textarea
              label="Pickup instructions (shown to driver)"
              placeholder="e.g. Ask for Luis at the parts counter"
              autosize
              minRows={1}
              {...form.getInputProps('pickup_instructions')}
            />
          )}
          {hasPickup && (
            <Checkbox
              label="Ready for pickup now"
              description="Untick if the shipper is not ready; mark it ready later from Packages (the driver is alerted)."
              {...form.getInputProps('ready_for_pickup', { type: 'checkbox' })}
            />
          )}

          {form.values.type === 'delivery' && (
            <TextInput
              withAsterisk
              label="Delivery address"
              placeholder="Street, city, state (e.g. 222 W Merchandise Mart Plaza, Chicago, IL)"
              description="Street and number is enough for Chicago; add the city for suburbs."
              {...form.getInputProps('dest_address')}
            />
          )}
          {isDelivery && <MatchLine status={addressStatus} match={addressMatch} />}

          {form.values.type === 'delivery' && (
            <Group grow>
              <TextInput
                label="Suite / floor / dock"
                placeholder="e.g. Suite 2000, 20th floor"
                {...form.getInputProps('dest_unit')}
              />
            </Group>
          )}

          {form.values.type === 'delivery' && (
            <Textarea
              label="Delivery instructions (shown to driver)"
              placeholder="e.g. Leave with concierge; loading dock on Franklin St"
              autosize
              minRows={2}
              {...form.getInputProps('delivery_instructions')}
            />
          )}

          {form.values.type === 'pickup' && (
            <TextInput
              label="Package ID (optional)"
              placeholder="Enter package ID"
              {...form.getInputProps('package_id')}
            />
          )}

          <Textarea
            label="Internal notes (not shown to driver)"
            placeholder="Optional details for dispatch..."
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
