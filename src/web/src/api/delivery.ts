import apiClient, { API_URL } from "./client";
import type { ProofOfDelivery } from "../types";

export async function getRecentProofs(): Promise<ProofOfDelivery[]> {
  const response = await apiClient.get("/delivery/recent-proofs");
  // Map backend response to frontend type
  return (response.data as Array<{
    packageId: string;
    driverId: string;
    timestamp: string;
    filename: string;
    url: string;
  }>).map((p) => ({
    filename: p.filename,
    packageId: p.packageId,
    driverId: p.driverId,
    timestamp: p.timestamp,
    // S3 presigned URLs are absolute; local URLs are relative paths
    url: p.url.startsWith("http") ? p.url : `${API_URL}${p.url}`,
  }));
}

export function getProofImageUrl(filename: string): string {
  return `${API_URL}/delivery/proof/${encodeURIComponent(filename)}`;
}

export async function confirmDelivery(
  packageId: string,
  driverId: string,
  photo: File
): Promise<{ status: string; package_id: string }> {
  const formData = new FormData();
  formData.append("package_id", packageId);
  formData.append("driver_id", driverId);
  formData.append("photo", photo);
  const response = await apiClient.post("/delivery/confirm", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function reportException(
  packageId: string,
  driverId: string,
  reason: string
): Promise<{ status: string; package_id: string; reason: string }> {
  const formData = new FormData();
  formData.append("package_id", packageId);
  formData.append("driver_id", driverId);
  formData.append("reason", reason);
  const response = await apiClient.post("/delivery/exception", formData);
  return response.data;
}
