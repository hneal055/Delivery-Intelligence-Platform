import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system/legacy';
import * as apiClient from '../api/client';

const OFFLINE_QUEUE_KEY = '@delivery_offline_queue';

/**
 * Persists photo URI permanently to the document directory to avoid cache purges.
 */
async function preservePhotoFile(tempUri, packageId) {
  if (!tempUri) return null;
  try {
    const filename = `offline_${packageId}_${Date.now()}.jpg`;
    const destPath = `${FileSystem.documentDirectory}${filename}`;
    await FileSystem.copyAsync({ from: tempUri, to: destPath });
    return destPath;
  } catch (err) {
    console.warn('Failed to preserve photo locally, falling back to temp URI:', err);
    return tempUri;
  }
}

/**
 * Enqueues a delivery item to AsyncStorage.
 */
export async function enqueueOfflineDelivery(payload) {
  try {
    const existing = await getOfflineQueue();

    let permanentPhotoUri = payload.photoUri;
    if (payload.photoUri) {
      permanentPhotoUri = await preservePhotoFile(payload.photoUri, payload.package_id);
    }

    const queueItem = {
      id: `queue_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
      timestamp: new Date().toISOString(),
      package_id: payload.package_id,
      driver_id: payload.driver_id || 'D001',
      dest_lat: String(payload.dest_lat),
      dest_lon: String(payload.dest_lon),
      signature_path: payload.signature_path || '',
      status: payload.status || 'DELIVERED',
      photoUri: permanentPhotoUri,
      retryCount: 0,
    };

    existing.push(queueItem);
    await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(existing));
    return queueItem;
  } catch (err) {
    console.error('Failed to enqueue delivery:', err);
    throw err;
  }
}

/**
 * Retrieves all queued offline delivery items.
 */
export async function getOfflineQueue() {
  try {
    const data = await AsyncStorage.getItem(OFFLINE_QUEUE_KEY);
    return data ? JSON.parse(data) : [];
  } catch (err) {
    console.error('Failed to read offline queue:', err);
    return [];
  }
}

/**
 * Uploads a single queued record to the FastAPI backend.
 */
async function uploadQueuedItem(item, baseUrl) {
  if (item.photoUri) {
    const uploadResponse = await FileSystem.uploadAsync(
      `${baseUrl}/delivery/confirm`,
      item.photoUri,
      {
        fieldName: 'photo',
        httpMethod: 'POST',
        uploadType: FileSystem.FileSystemUploadType.MULTIPART,
        parameters: {
          package_id: String(item.package_id),
          driver_id: String(item.driver_id),
          dest_lat: String(item.dest_lat),
          dest_lon: String(item.dest_lon),
          signature_path: item.signature_path || '',
          status: item.status || 'DELIVERED',
        },
      }
    );

    if (uploadResponse.status < 200 || uploadResponse.status >= 300) {
      throw new Error(`Server returned ${uploadResponse.status}`);
    }

    try {
      await FileSystem.deleteAsync(item.photoUri, { idempotent: true });
    } catch {}

    return JSON.parse(uploadResponse.body);
  } else {
    const params = new URLSearchParams();
    params.append('package_id', item.package_id);
    params.append('driver_id', item.driver_id);
    params.append('dest_lat', item.dest_lat);
    params.append('dest_lon', item.dest_lon);
    if (item.signature_path) params.append('signature_path', item.signature_path);
    params.append('status', item.status || 'DELIVERED');

    const response = await fetch(`${baseUrl}/delivery/confirm`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: params.toString(),
    });

    if (!response.ok) {
      throw new Error(`Server returned ${response.status}`);
    }

    return await response.json();
  }
}

/**
 * Flushes the queue against the FastAPI server.
 */
export async function syncOfflineQueue() {
  const queue = await getOfflineQueue();
  if (queue.length === 0) return { syncedCount: 0, remainingCount: 0 };

  const baseUrl = apiClient.BASE_URL || 'http://192.168.12.196:8000';
  const remaining = [];
  let syncedCount = 0;

  for (const item of queue) {
    try {
      await uploadQueuedItem(item, baseUrl);
      syncedCount++;
    } catch (err) {
      console.warn(`Failed to sync item ${item.package_id}:`, err.message);
      remaining.push({ ...item, retryCount: (item.retryCount || 0) + 1 });
    }
  }

  await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(remaining));
  return { syncedCount, remainingCount: remaining.length };
}