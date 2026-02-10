import apiClient from "./client";
import type { 
  Driver, 
  Package, 
  DashboardSummary, 
  LiveDriverLocation,
  DispatchJob,
  DispatchJobCreate,
  DriverAvailability,
  DriverAvailabilityCreate
} from "../types";

export async function listDrivers(status?: string): Promise<Driver[]> {
  const params: Record<string, string> = {};
  if (status) params.status = status;
  const response = await apiClient.get<Driver[]>("/dispatch/drivers", { params });
  return response.data;
}

export async function getDriverPackages(driverId: string, status?: string): Promise<Package[]> {
  const params: Record<string, string> = {};
  if (status) params.status = status;
  const response = await apiClient.get<Package[]>(`/dispatch/drivers/${driverId}/packages`, { params });
  return response.data;
}

export async function listPackages(status?: string, driverId?: string): Promise<Package[]> {
  const params: Record<string, string> = {};
  if (status) params.status = status;
  if (driverId) params.driver_id = driverId;
  const response = await apiClient.get<Package[]>("/dispatch/packages", { params });
  return response.data;
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const response = await apiClient.get<DashboardSummary>("/dispatch/dashboard/summary");
  return response.data;
}

export async function getLiveLocations(): Promise<LiveDriverLocation[]> {
  const response = await apiClient.get<LiveDriverLocation[]>("/tracking/live");
  return response.data;
}

// -- New Scheduling / Dispatch Job Endpoints --

export async function listJobs(
  start_time?: string,
  end_time?: string,
  driver_id?: string,
  status?: string
): Promise<DispatchJob[]> {
  const params: Record<string, string> = {};
  if (start_time) params.start_time = start_time;
  if (end_time) params.end_time = end_time;
  if (driver_id) params.driver_id = driver_id;
  if (status) params.status = status;

  const response = await apiClient.get<DispatchJob[]>("/dispatch/jobs", { params });
  return response.data;
}

export async function createJob(job: DispatchJobCreate): Promise<DispatchJob> {
  const response = await apiClient.post<DispatchJob>("/dispatch/jobs", job);
  return response.data;
}

export async function assignJob(jobId: string, driverId: string): Promise<DispatchJob> {
  const response = await apiClient.put<DispatchJob>(`/dispatch/jobs/${jobId}/assign`, null, {
    params: { driver_id: driverId }
  });
  return response.data;
}

export async function updateJobStatus(jobId: string, status: string): Promise<DispatchJob> {
  const response = await apiClient.put<DispatchJob>(`/dispatch/jobs/${jobId}/status?status=${status}`);
  return response.data;
}

export async function deleteJob(jobId: string): Promise<void> {
  await apiClient.delete(`/dispatch/jobs/${jobId}`);
}

// -- Availability Endpoints --

export async function getAvailability(
  start_date: string,
  end_date: string,
  driver_id?: string
): Promise<DriverAvailability[]> {
  const params: Record<string, string> = { start_date, end_date };
  if (driver_id) params.driver_id = driver_id;

  const response = await apiClient.get<DriverAvailability[]>("/dispatch/availability/", { params });
  return response.data;
}

export async function setAvailability(availability: DriverAvailabilityCreate): Promise<DriverAvailability> {
  const response = await apiClient.post<DriverAvailability>("/dispatch/availability/", availability);
  return response.data;
}

export async function getLocationHistory(driverId: string, hours: number = 24): Promise<LiveDriverLocation[]> {
  const response = await apiClient.get<LiveDriverLocation[]>(`/tracking/${driverId}/history`, {
    params: { hours }
  });
  return response.data;
}
