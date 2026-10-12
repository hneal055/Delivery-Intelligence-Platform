import { Modal, TextInput, Button, Group, Textarea, Select, Stack, Text, Checkbox, Anchor } from '@mantine/core';
import { useForm } from '@mantine/form';
import { useDispatch } from '../../hooks/useDispatch';
import { useDrivers } from '../../hooks/useDrivers';
import { JOB_TYPES } from '../../constants/dispatch';
import type { JobType } from '../../constants/dispatch';
import { useAddressPreview } from '../../hooks/useAddressPreview';
import type { AddressMatch } from '../../types';
import type { AddressStatus } from '../../hooks/useAddressPreview';

function MatchLine({ status, match, value, onUse }: {
  status: AddressStatus;
  match: AddressMatch | null;
  value: string;
  onUse: (address: string) => void;
}) {
  if (status === 'idle') return null;
  const color = status === 'found' ? (match?.used_default_area ? 'orange' : 'teal') : status === 'missing' ? 'red' : 'dimmed';
  // Offer the matched address as the entry unless it is already what's typed.
  const canUse = status === 'found' && match && match.matched_address.toLowerCase() !== value.trim().toLowerCase();
  return (
    <Text size="sm" c={color}>
      {status === 'checking' && 'Checking address…'}
      {status === 'missing' && 'No match yet. Add the city and state, or a ZIP code.'}
      {status === 'found' && match &&
        `Matched: ${match.matched_address}${match.used_default_area ? ' (Chicago assumed; add the city if this is a suburb)' : ''}`}
      {canUse && (
        <>
          {' '}
          <Anchor component="button" type="button" size="sm" fw={600} onClick={() => onUse(match.matched_address)}>
            Use this
          </Anchor>
        </>
      )}
    </Text>
  );
}

interface CreateJobModalProps {
  opened: boolean;
  onClose: () => void;
}

const GRACE_MINUTES = 5;

// The browser's own date-and-time box (US order, AM/PM, typeable) works with
// local "YYYY-MM-DDTHH:mm" text; convert to a Date only when checking or saving.
function toLocalInputValue(date: Date) {
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function parseLocalInput(value: string): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

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
      scheduled_at: toLocalInputValue(now),
      driver_id: '',
      dest_address: '',
      dest_unit: '',
      delivery_instructions: '',
      recipient_name: '',
      recipient_phone: '',
      pickup_contact_name: '',
      pickup_contact_phone: '',
      pickup_address: '',
      pickup_instructions: '',
      ready_for_pickup: true,
      status: 'pending',
    },
    validate: {
      title: (value, values) => {
        const trimmed = value.trim();
        if (trimmed.length < 2) return 'Title must be at least 2 characters';
        const scheduledAt = parseLocalInput(values.scheduled_at);
        if (!scheduledAt) return null;

        const scheduledDay = getLocalDayKey(scheduledAt);
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
        const scheduledAt = parseLocalInput(value);
        if (!scheduledAt) return 'Pick a date and time';
        return scheduledAt < minScheduledAt ? 'Scheduled time must be in the future' : null;
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
        if (values.type !== 'delivery' && values.type !== 'pickup') return null;
        return value.trim().length >= 5 ? null : 'Where the package goes is required';
      },
      pickup_address: (value, values) => {
        if (values.type !== 'pickup') return null;
        return value.trim().length >= 5 ? null : 'Pickup address is required';
      },
    },
  });

  // Live address check: show what the address matches before saving, so a
  // default-city guess is never saved unseen.
  // Delivery and Pickup jobs both move a package from A (optional for a
  // delivery: it may start in the van) to B.
  const isPickupJob = form.values.type === 'pickup';
  const isDelivery = form.values.type === 'delivery' || isPickupJob;
  const { match: addressMatch, status: addressStatus } = useAddressPreview(form.values.dest_address, isDelivery);
  const hasPickup = isDelivery && (isPickupJob || form.values.pickup_address.trim().length > 0);
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
        scheduled_at: parseLocalInput(values.scheduled_at)!.toISOString(),
        driver_id: values.driver_id || undefined,
        dest_address: isDelivery ? values.dest_address.trim() || undefined : undefined,
        dest_unit: isDelivery ? values.dest_unit.trim() || undefined : undefined,
        delivery_instructions: isDelivery ? values.delivery_instructions.trim() || undefined : undefined,
        pickup_address: isDelivery ? values.pickup_address.trim() || undefined : undefined,
        pickup_instructions: isDelivery ? values.pickup_instructions.trim() || undefined : undefined,
        recipient_name: isDelivery ? values.recipient_name.trim() || undefined : undefined,
        recipient_phone: isDelivery ? values.recipient_phone.trim() || undefined : undefined,
        pickup_contact_name: hasPickup ? values.pickup_contact_name.trim() || undefined : undefined,
        pickup_contact_phone: hasPickup ? values.pickup_contact_phone.trim() || undefined : undefined,
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
          const pickupProblem = typeof detail === 'string' && detail.startsWith('Pickup');
          form.setFieldError(
            !isDelivery ? 'title' : pickupProblem ? 'pickup_address' : 'dest_address',
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

          <TextInput
            type="datetime-local"
            withAsterisk
            label="Scheduled Time"
            description="Type it or click the calendar icon"
            min={toLocalInputValue(minScheduledAt)}
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
              withAsterisk={isPickupJob}
              label={isPickupJob ? 'Pickup address' : 'Pickup address (optional)'}
              placeholder={
                isPickupJob
                  ? 'Where the driver collects it'
                  : 'Where the driver collects it; leave blank if it starts in the van'
              }
              {...form.getInputProps('pickup_address')}
            />
          )}
          {isDelivery && <MatchLine status={pickupStatus} match={pickupMatch} value={form.values.pickup_address} onUse={(a) => form.setFieldValue('pickup_address', a)} />}
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
            <Group grow>
              <TextInput label="Pickup contact" placeholder="e.g. Luis" {...form.getInputProps('pickup_contact_name')} />
              <TextInput label="Pickup phone" placeholder="(773) 555-0199" {...form.getInputProps('pickup_contact_phone')} />
            </Group>
          )}
          {hasPickup && (
            <Checkbox
              label="Ready for pickup now"
              description="Untick if the shipper is not ready; mark it ready later from Packages (the driver is alerted)."
              {...form.getInputProps('ready_for_pickup', { type: 'checkbox' })}
            />
          )}

          {isDelivery && (
            <TextInput
              withAsterisk
              label={isPickupJob ? 'Deliver to (customer or your depot)' : 'Delivery address'}
              placeholder="Street, city, state (e.g. 222 W Merchandise Mart Plaza, Chicago, IL)"
              description="Street and number is enough for Chicago; add the city for suburbs."
              {...form.getInputProps('dest_address')}
            />
          )}
          {isDelivery && <MatchLine status={addressStatus} match={addressMatch} value={form.values.dest_address} onUse={(a) => form.setFieldValue('dest_address', a)} />}

          {isDelivery && (
            <Group grow>
              <TextInput
                label="Suite / floor / dock"
                placeholder="e.g. Suite 2000, 20th floor"
                {...form.getInputProps('dest_unit')}
              />
            </Group>
          )}

          {isDelivery && (
            <Textarea
              label="Delivery instructions (shown to driver)"
              placeholder="e.g. Leave with concierge; loading dock on Franklin St"
              autosize
              minRows={2}
              {...form.getInputProps('delivery_instructions')}
            />
          )}
          {isDelivery && (
            <Group grow>
              <TextInput label="Recipient name" placeholder="Who receives it" {...form.getInputProps('recipient_name')} />
              <TextInput label="Recipient phone" placeholder="(312) 555-0142" {...form.getInputProps('recipient_phone')} />
            </Group>
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
