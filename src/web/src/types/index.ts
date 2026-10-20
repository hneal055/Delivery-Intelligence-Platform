import type { JobType } from "../constants/dispatch";

export interface Location {
  lat: number;
  lon: number;
  address?: string;
}

export interface Driver {
  id: string;
  name: string;
  status: string;
  current_lat: number | null;
  current_lon: number | null;
  last_updated: string | null;
  package_count: number;
  is_online: boolean;
}

export interface Package {
  id: string;
  driver_id: string | null;
  vehicle_id: string | null;
  dest_lat: number;
  dest_lon: number;
  dest_address: string | null;
  dest_unit: string | null;
  delivery_instructions: string | null;
  pickup_address: string | null;
  pickup_lat: number | null;
  pickup_lon: number | null;
  pickup_instructions: string | null;
  ready_at: string | null;
  /** Time promised to the customer, if any (UTC ISO) */
  deliver_by: string | null;
  exception_reason: string | null;
  tracking_code: string | null;
  recipient_name: string | null;
  recipient_phone: string | null;
  pickup_contact_name: string | null;
  pickup_contact_phone: string | null;
  status: string;
  section: string | null;
  distance_km: number | null;
  predicted_eta_seconds: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface User {
  id: string;
  username: string;
  email: string | null;
  role: "driver" | "dispatcher" | "manager" | "admin";
  is_active: boolean;
}

export interface Token {
  access_token: string;
  token_type: JobType;
}

/** An item on the Dashboard's "Needs attention" panel (GET /dispatch/attention). */
export interface AttentionItem {
  key: string;
  rule: "no_driver" | "overdue" | "problem" | "late" | "due_soon" | "ready_waiting" | "offline_ready" | "quiet" | "stopped";
  severity: "red" | "orange";
  title: string;
  detail: string;
  since: string | null;
  job_id: string | null;
  package_id: string | null;
  driver_id: string | null;
}

export interface DashboardSummary {
  total_drivers: number;
  active_drivers: number;
  online_drivers: number;
  total_packages: number;
  pending_packages: number;
  delivered_packages: number;
  exception_packages: number;
  /** Last 7 days, packages that had a deliver-by time */
  on_time_delivered: number;
  on_time_total: number;
}

export interface LiveDriverLocation {
  driver_id: string;
  name: string;
  lat: number | null;
  lon: number | null;
  status: string;
  is_online: boolean;
  last_updated: string | null;
}

export interface DriverLocationUpdate {
  type: "driver_location";
  driver_id: string;
  lat: number;
  lon: number;
  speed_kmh?: number;
  heading?: number;
  timestamp: number;
}

export interface DriverStatusUpdate {
  type: "driver_status";
  driver_id: string;
  status: string;
  timestamp: number;
}

export type WebSocketMessage = DriverLocationUpdate | DriverStatusUpdate | { type: JobType; [key: string]: unknown };


export interface DispatchJob {
  id: string;
  package_id: string | null;
  driver_id: string | null;
  title: string;
  type: JobType;
  status: string;
  priority: string;
  notes: string | null;
  scheduled_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface PackageWorkspaceUpdate {
  driver_id: string | null;
  dest_address: string;
  dest_unit: string;
  delivery_instructions: string;
  pickup_address: string;
  pickup_instructions: string;
  recipient_name: string;
  recipient_phone: string;
  pickup_contact_name: string;
  pickup_contact_phone: string;
  deliver_by: string | null;
  scheduled_at: string | null;
  ready_for_pickup: boolean;
  priority: string;
  job_title: string;
  job_notes: string;
}

export interface DispatchJobCreate {
  driver_id?: string;
  title: string;
  type?: JobType;
  priority?: string;
  notes?: string;
  scheduled_at?: string;
  package_id?: string;
  dest_address?: string;
  dest_unit?: string;
  delivery_instructions?: string;
  pickup_address?: string;
  pickup_instructions?: string;
  ready_for_pickup?: boolean;
  recipient_name?: string;
  recipient_phone?: string;
  pickup_contact_name?: string;
  pickup_contact_phone?: string;
  deliver_by?: string;
}

export interface AddressMatch {
  matched_address: string;
  lat: number;
  lon: number;
  used_default_area: boolean;
}

export interface DriverAvailability {
  id: string;
  driver_id: string;
  date: string;
  is_available: boolean;
  start_time: string | null;
  end_time: string | null;
}

export interface DriverAvailabilityCreate {
  driver_id: string;
  date: string;
  is_available: boolean;
  start_time?: string;
  end_time?: string;
}

export interface ProofOfDelivery {
  filename: string;
  packageId: string;
  driverId: string;
  timestamp: string;
  url: string;
  /** API path of the photo (needs the login token; see useAuthedImage) */
  path: string;
  receivedBy: string | null;
  signature: string | null;
  distanceMeters: number | null;
}

export interface LocationHistoryPoint {
  id: number;
  driver_id: string;
  lat: number;
  lon: number;
  speed: number | null;
  heading: number | null;
  battery_level: number | null;
  timestamp: string;
}

export interface Equipment {
  id: string;
  barcode: string;
  name: string;
  type: JobType;
  status: "available" | "checked_out" | "maintenance";
  checked_out_by: string | null;
  checked_out_at: string | null;
  notes: string | null;
}

export interface EquipmentScanEvent {
  equipment_id: string;
  barcode: string;
  action: "check_in" | "check_out";
  driver_id: string;
  timestamp: string;
}
