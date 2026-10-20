import { useEffect, useMemo, useRef } from "react";
import {
  Badge,
  Button,
  Divider,
  Drawer,
  Group,
  Select,
  Stack,
  Switch,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { useForm } from "@mantine/form";
import { notifications } from "@mantine/notifications";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getRecentProofs } from "../../api/delivery";
import {
  listJobs,
  markPackageReady,
  reopenPackage,
  updatePackageWorkspace,
} from "../../api/dispatch";
import { useDrivers } from "../../hooks/useDrivers";
import type { DispatchJob, Package, PackageWorkspaceUpdate } from "../../types";

interface PackageWorkspaceDrawerProps {
  pkg: Package | null;
  opened: boolean;
  onClose: () => void;
}

interface WorkspaceFormValues {
  driver_id: string;
  dest_address: string;
  dest_unit: string;
  delivery_instructions: string;
  pickup_address: string;
  pickup_instructions: string;
  recipient_name: string;
  recipient_phone: string;
  pickup_contact_name: string;
  pickup_contact_phone: string;
  deliver_by: string;
  scheduled_at: string;
  ready_for_pickup: boolean;
  priority: string;
  job_title: string;
  job_notes: string;
}

function toLocalDateTime(value: string | null | undefined): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 16);
}

function toIso(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

function statusLabel(status: string): string {
  if (status === "loaded") return "Picked up";
  if (status === "exception") return "Problem reported";
  return status;
}

function linkedJobFor(pkg: Package, jobs: DispatchJob[]): DispatchJob | undefined {
  return jobs.find(
    (job) => job.package_id === pkg.id && !["completed", "cancelled"].includes(job.status)
  );
}

export function PackageWorkspaceDrawer({
  pkg,
  opened,
  onClose,
}: PackageWorkspaceDrawerProps) {
  const queryClient = useQueryClient();
  const { data: drivers = [] } = useDrivers();
  const { data: jobs = [], isLoading: jobsLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => listJobs(),
    enabled: opened,
    refetchInterval: 30000,
  });
  const { data: proofs = [], isLoading: proofsLoading } = useQuery({
    queryKey: ["package-proofs", pkg?.id],
    queryFn: () => getRecentProofs(pkg!.id),
    enabled: opened && Boolean(pkg?.id),
  });

  const linkedJob = useMemo(
    () => (pkg ? linkedJobFor(pkg, jobs) : undefined),
    [pkg, jobs]
  );
  const finalPackage = pkg?.status === "delivered" || pkg?.status === "exception";

  const form = useForm<WorkspaceFormValues>({
    initialValues: {
      driver_id: "",
      dest_address: "",
      dest_unit: "",
      delivery_instructions: "",
      pickup_address: "",
      pickup_instructions: "",
      recipient_name: "",
      recipient_phone: "",
      pickup_contact_name: "",
      pickup_contact_phone: "",
      deliver_by: "",
      scheduled_at: "",
      ready_for_pickup: false,
      priority: "medium",
      job_title: "",
      job_notes: "",
    },
  });
  const initialValues = useRef<WorkspaceFormValues | null>(null);

  useEffect(() => {
    if (!pkg) return;
    const values: WorkspaceFormValues = {
      driver_id: pkg.driver_id ?? "",
      dest_address: pkg.dest_address ?? "",
      dest_unit: pkg.dest_unit ?? "",
      delivery_instructions: pkg.delivery_instructions ?? "",
      pickup_address: pkg.pickup_address ?? "",
      pickup_instructions: pkg.pickup_instructions ?? "",
      recipient_name: pkg.recipient_name ?? "",
      recipient_phone: pkg.recipient_phone ?? "",
      pickup_contact_name: pkg.pickup_contact_name ?? "",
      pickup_contact_phone: pkg.pickup_contact_phone ?? "",
      deliver_by: toLocalDateTime(pkg.deliver_by),
      scheduled_at: toLocalDateTime(linkedJob?.scheduled_at),
      ready_for_pickup: Boolean(pkg.ready_at),
      priority: linkedJob?.priority ?? "medium",
      job_title: linkedJob?.title ?? "",
      job_notes: linkedJob?.notes ?? "",
    };
    initialValues.current = values;
    form.setInitialValues(values);
    form.setValues(values);
    form.resetDirty(values);
  }, [opened, pkg?.id, linkedJob?.id]);

  const refreshWorkspace = () => {
    void queryClient.invalidateQueries({ queryKey: ["packages"] });
    void queryClient.invalidateQueries({ queryKey: ["attention"] });
    void queryClient.invalidateQueries({ queryKey: ["jobs"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard-summary"] });
    void queryClient.invalidateQueries({ queryKey: ["package-proofs", pkg?.id] });
  };
  const showError = (error: unknown) => {
    const detail = (error as { response?: { data?: { detail?: string } } }).response?.data?.detail;
    notifications.show({
      color: "red",
      title: "Could not update package",
      message: detail ?? "The server rejected the update. Please try again.",
    });
  };

  const save = useMutation({
    mutationFn: (update: Partial<PackageWorkspaceUpdate>) =>
      updatePackageWorkspace(pkg!.id, update),
    onSuccess: () => {
      notifications.show({ color: "teal", title: "Package updated", message: "Package and linked schedule were saved." });
      initialValues.current = form.values;
      form.setInitialValues(form.values);
      form.resetDirty(form.values);
      refreshWorkspace();
    },
    onError: showError,
  });
  const markReady = useMutation({
    mutationFn: () => markPackageReady(pkg!.id),
    onSuccess: () => {
      notifications.show({ color: "teal", title: "Pickup marked ready", message: "The assigned driver was alerted." });
      refreshWorkspace();
    },
    onError: showError,
  });
  const reopen = useMutation({
    mutationFn: () => reopenPackage(pkg!.id),
    onSuccess: () => {
      notifications.show({ color: "teal", title: "Package reopened", message: "The package is back in the active workflow." });
      refreshWorkspace();
    },
    onError: showError,
  });

  const saveForm = (values: WorkspaceFormValues) => {
    const initial = initialValues.current;
    if (!initial) return;
    const update: Partial<PackageWorkspaceUpdate> = {};
    const textFields = [
      "dest_address",
      "dest_unit",
      "delivery_instructions",
      "pickup_address",
      "pickup_instructions",
      "recipient_name",
      "recipient_phone",
      "pickup_contact_name",
      "pickup_contact_phone",
    ] as const;
    for (const field of textFields) {
      if (values[field] !== initial[field]) update[field] = values[field].trim();
    }
    if (values.driver_id !== initial.driver_id) {
      update.driver_id = values.driver_id || null;
    }
    if (values.deliver_by !== initial.deliver_by) {
      update.deliver_by = toIso(values.deliver_by);
    }
    if (values.ready_for_pickup !== initial.ready_for_pickup) {
      update.ready_for_pickup = values.ready_for_pickup;
    }
    if (linkedJob) {
      if (values.scheduled_at !== initial.scheduled_at) {
        update.scheduled_at = toIso(values.scheduled_at);
      }
      if (values.priority !== initial.priority) update.priority = values.priority;
      if (values.job_title !== initial.job_title) update.job_title = values.job_title.trim();
      if (values.job_notes !== initial.job_notes) update.job_notes = values.job_notes.trim();
    }
    if (Object.keys(update).length === 0) {
      notifications.show({ color: "gray", title: "No changes", message: "Nothing to save." });
      return;
    }
    save.mutate(update);
  };

  const copyTrackingLink = async () => {
    if (!pkg?.tracking_code) return;
    const url = `${window.location.origin}/track/${pkg.tracking_code}`;
    try {
      await navigator.clipboard.writeText(url);
      notifications.show({ color: "teal", title: "Tracking link copied", message: url });
    } catch {
      notifications.show({ color: "orange", title: "Copy this tracking link", message: url, autoClose: false });
    }
  };

  return (
    <Drawer
      opened={opened}
      onClose={onClose}
      title="Package workspace"
      position="right"
      size="xl"
      overlayProps={{ backgroundOpacity: 0.35, blur: 1 }}
    >
      {!pkg ? (
        <Text c="dimmed">Select a package to view its workspace.</Text>
      ) : (
        <form onSubmit={form.onSubmit(saveForm)}>
          <Stack gap="md">
            <Group justify="space-between" align="flex-start">
              <Stack gap={4}>
                <Text fw={700} size="lg">
                  {pkg.tracking_code ?? `Package ${pkg.id.slice(0, 8)}`}
                </Text>
                <Text size="xs" c="dimmed">Package ID: {pkg.id}</Text>
              </Stack>
              <Badge color={pkg.status === "delivered" ? "teal" : pkg.status === "exception" ? "red" : "blue"}>
                {statusLabel(pkg.status)}
              </Badge>
            </Group>
            {pkg.tracking_code && (
              <Button variant="light" size="xs" onClick={copyTrackingLink}>
                Copy public tracking link
              </Button>
            )}

            <Divider label="Delivery and recipient" />
            <TextInput label="Delivery address" required {...form.getInputProps("dest_address")} />
            <TextInput label="Suite / unit" {...form.getInputProps("dest_unit")} />
            <Textarea label="Delivery instructions" autosize minRows={2} {...form.getInputProps("delivery_instructions")} />
            <Group grow>
              <TextInput label="Recipient name" {...form.getInputProps("recipient_name")} />
              <TextInput label="Recipient phone" {...form.getInputProps("recipient_phone")} />
            </Group>

            <Divider label="Pickup" />
            <TextInput label="Pickup address (leave blank if not applicable)" {...form.getInputProps("pickup_address")} />
            <Textarea label="Pickup instructions" autosize minRows={2} {...form.getInputProps("pickup_instructions")} />
            <Group grow>
              <TextInput label="Pickup contact" {...form.getInputProps("pickup_contact_name")} />
              <TextInput label="Pickup contact phone" {...form.getInputProps("pickup_contact_phone")} />
            </Group>
            <Switch
              label="Ready for pickup"
              disabled={["loaded", "delivered", "exception"].includes(pkg.status)}
              {...form.getInputProps("ready_for_pickup", { type: "checkbox" })}
            />

            <Divider label="Assignment and schedule" />
            <Select
              label="Assigned driver"
              data={[
                { value: "", label: "Unassigned" },
                ...drivers.map((driver) => ({ value: driver.id, label: `${driver.name} (${driver.id})` })),
              ]}
              disabled={finalPackage}
              {...form.getInputProps("driver_id")}
            />
            {jobsLoading ? (
              <Text size="sm" c="dimmed">Loading linked scheduling data…</Text>
            ) : linkedJob ? (
              <>
                <TextInput label="Dispatch job title" {...form.getInputProps("job_title")} />
                <Group grow>
                  <TextInput label="Scheduled pickup / dispatch" type="datetime-local" {...form.getInputProps("scheduled_at")} />
                  <TextInput label="Promised delivery by" type="datetime-local" {...form.getInputProps("deliver_by")} />
                </Group>
                <Select
                  label="Priority"
                  data={["low", "medium", "high", "urgent"]}
                  {...form.getInputProps("priority")}
                />
                <Textarea label="Dispatch notes" autosize minRows={2} {...form.getInputProps("job_notes")} />
                <Text size="xs" c="dimmed">Job {linkedJob.id} · {linkedJob.status}</Text>
              </>
            ) : (
              <>
                <TextInput label="Promised delivery by" type="datetime-local" {...form.getInputProps("deliver_by")} />
                <Text size="sm" c="orange">
                  No linked dispatch job was found. Assignment and dispatch scheduling are unavailable until a job is linked.
                </Text>
              </>
            )}

            {pkg.exception_reason && (
              <Text size="sm" c="red">Problem reported: {pkg.exception_reason}</Text>
            )}
            <Group>
              {pkg.pickup_address && !pkg.ready_at && ["pending", "assigned"].includes(pkg.status) && (
                <Button
                  variant="light"
                  loading={markReady.isPending}
                  onClick={() => markReady.mutate()}
                >
                  Mark pickup ready
                </Button>
              )}
              {pkg.status === "exception" && (
                <Button color="red" variant="light" loading={reopen.isPending} onClick={() => reopen.mutate()}>
                  Reopen package
                </Button>
              )}
            </Group>

            <Divider label="Delivery proof" />
            {proofsLoading ? (
              <Text size="sm" c="dimmed">Loading delivery records…</Text>
            ) : proofs.length ? (
              proofs.map((proof) => (
                <Stack key={proof.filename} gap={2}>
                  <Text size="sm" fw={500}>Confirmed {new Date(proof.timestamp).toLocaleString()}</Text>
                  <Text size="sm">Driver: {proof.driverId}{proof.receivedBy ? ` · Received by ${proof.receivedBy}` : ""}</Text>
                  {proof.distanceMeters != null && (
                    <Text size="xs" c="dimmed">Recorded {Math.round(proof.distanceMeters)} m from destination</Text>
                  )}
                </Stack>
              ))
            ) : (
              <Text size="sm" c="dimmed">No delivery proof has been received for this package.</Text>
            )}
            <Text size="xs" c="dimmed">
              Created {pkg.created_at ? new Date(pkg.created_at).toLocaleString() : "date unavailable"}
              {pkg.updated_at ? ` · Updated ${new Date(pkg.updated_at).toLocaleString()}` : ""}
            </Text>

            <Group justify="flex-end" mt="sm">
              <Button variant="default" onClick={onClose}>Close</Button>
              <Button type="submit" loading={save.isPending} disabled={jobsLoading}>
                Save changes
              </Button>
            </Group>
          </Stack>
        </form>
      )}
    </Drawer>
  );
}
