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
  role: "driver" | "manager" | "admin";
  is_active: boolean;
}

export interface Token {
  access_token: string;
  token_type: JobType;
}

export interface DashboardSummary {
  total_drivers: number;
  active_drivers: number;
  online_drivers: number;
  total_packages: number;
  pending_packages: number;
  delivered_packages: number;
  exception_packages: number;
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

export interface DispatchJobCreate {
  driver_id?: string;
  title: string;
  type?: JobType;
  priority?: string;
  notes?: string;
  scheduled_at?: string;
  package_id?: string;
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

