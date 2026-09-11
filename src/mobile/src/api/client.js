import { Platform } from 'react-native';

// Dynamically select the correct host depending on the platform or environment override
const getDefaultHost = () => {
  if (process.env.EXPO_PUBLIC_API_HOST) {
    return process.env.EXPO_PUBLIC_API_HOST;
  }
  // Android Emulator requires 10.0.2.2 to reach the host machine's localhost
  return Platform.OS === 'android' ? '10.0.2.2' : 'localhost';
};

const API_HOST = getDefaultHost();
const API_PORT = process.env.EXPO_PUBLIC_API_PORT || '8000';

export const BASE_URL = `http://${API_HOST}:${API_PORT}`;

/**
 * Fetch route manifest for driver with optional GPS coordinate optimization.
 * When originLat and originLon are supplied, the backend performs a 
 * nearest-neighbor TSP sort.
 */
export async function getSampleRoute(driverId = 'D001', originLat = null, originLon = null) {
  let url = `${BASE_URL}/routing/sample-route/${driverId}`;
  const queryParams = [];

  if (originLat !== null && originLon !== null) {
    queryParams.push(`origin_lat=${originLat}`);
    queryParams.push(`origin_lon=${originLon}`);
    queryParams.push('optimize=true');
  }

  if (queryParams.length > 0) {
    url += `?${queryParams.join('&')}`;
  }

  const response = await fetch(url);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch route (${response.status}): ${errorText}`);
  }

  return await response.json();
}

/**
 * Fetch recently submitted delivery proof records from SQLite.
 */
export async function getRecentProofs(limit = 20) {
  const response = await fetch(`${BASE_URL}/delivery/recent-proofs?limit=${limit}`);
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to fetch proofs (${response.status}): ${errorText}`);
  }

  return await response.json();
}

/**
 * Fallback confirmation method for non-file/FormData uploads.
 */
export async function confirmDelivery(formData) {
  const response = await fetch(`${BASE_URL}/delivery/confirm`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Server returned ${response.status}: ${errorText}`);
  }

  return await response.json();
}

/**
 * Trigger backend database and media reset.
 */
export async function resetDatabase() {
  const response = await fetch(`${BASE_URL}/debug/reset-db`, {
    method: 'POST',
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to reset database (${response.status}): ${errorText}`);
  }

  return await response.json();
}