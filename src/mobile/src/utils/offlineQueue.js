import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system/legacy';
import * as ImageManipulator from 'expo-image-manipulator';
import * as apiClient from '../api/client';

const OFFLINE_QUEUE_KEY = '@delivery_offline_queue';
const SINGLE_ITEM_TIMEOUT_MS = 12000; // 12-second ceiling per delivery

/**
 * Helper to get file size in KB/MB for verification.
 */
async function getFileSizeString(uri) {
  try {
    const info = await FileSystem.getInfoAsync(uri);
    if (!info.exists || !info.size) return 'unknown size';
    const kb = (info.size / 1024).toFixed(1);
    if (info.size > 1024 * 1024) {
      return `${(info.size / (1024 * 1024)).toFixed(2)} MB`;
    }
    return `${kb} KB`;
  } catch {
    return 'unknown size';
  }
}

/**
 * Optimizes and persists photo to documentDirectory with diagnostic logging.
 */
async function compressAndPreservePhoto(tempUri, packageId) {
  if (!tempUri) return null;

  try {
    const originalSize = await getFileSizeString(tempUri);

    console.log(`[Compression] Starting optimization for ${packageId} (Original: ${originalSize})`);

    const manipulated = await ImageManipulator.manipulateAsync(
      tempUri,
      [{ resize: { width: 1024 } }],
      { compress: 0.6, format: ImageManipulator.SaveFormat.JPEG }
    );

    const compressedSize = await getFileSizeString(manipulated.uri);
    console.log(`[Compression] Completed for ${packageId}: ${originalSize} -> ${compressedSize}`);

    const filename = `offline_${packageId}_${Date.now()}.jpg`;
    const destPath = `${FileSystem.documentDirectory}${filename}`;

    await FileSystem.copyAsync({ from: manipulated.uri, to: destPath });

    try {
      await FileSystem.deleteAsync(manipulated.uri, { idempotent: true });
    } catch {}

    return destPath;
  } catch (err) {
    console.warn('[Compression Error] Fallback to raw photo URI:', err.message);
    return tempUri;
  }
}

/**
 * Enqueues a delivery item to AsyncStorage.
 */
export async function enqueueOfflineDelivery(payload) {
  try {
    const existing = await getOfflineQueue();

    let permanentPhotoUri = null;
    if (payload.photoUri) {
      permanentPhotoUri = await compressAndPreservePhoto(payload.photoUri, payload.package_id);
    }

    const queueItem = {
      id: `queue_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
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
    console.log(`[OfflineQueue] Enqueued item: ${payload.package_id}. Total queued: ${existing.length}`);
    return queueItem;
  } catch (err) {
    console.error('[OfflineQueue] Failed to enqueue delivery:', err);
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
    console.error('[OfflineQueue] Failed to read queue:', err);
    return [];
  }
}

/**
 * Removes a specific single item from the queue immediately after success.
 */
async function removeQueueItemById(itemId) {
  try {
    const queue = await getOfflineQueue();
    const filtered = queue.filter((i) => i.id !== itemId);
    await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(filtered));
  } catch (err) {
    console.error('[OfflineQueue] Failed to prune queue item:', err);
  }
}

/**
 * Uploads a single queued record with timeout safeguard and console timing.
 */
async function uploadQueuedItemWithTimeout(item, baseUrl) {
  const startTime = Date.now();
  console.log(`[Sync] Uploading ${item.package_id}... (12s timeout armed)`);

  const uploadPromise = (async () => {
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

      const controller = new AbortController();
      const fetchTimer = setTimeout(() => controller.abort(), SINGLE_ITEM_TIMEOUT_MS);

      try {
        const response = await fetch(`${baseUrl}/delivery/confirm`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: params.toString(),
          signal: controller.signal,
        });

        if (!response.ok) {
          throw new Error(`Server status ${response.status}`);
        }

        return await response.json();
      } finally {
        clearTimeout(fetchTimer);
      }
    }
  })();

  const timeoutPromise = new Promise((_, reject) =>
    setTimeout(
      () => reject(new Error(`Upload timeout after ${SINGLE_ITEM_TIMEOUT_MS / 1000}s`)),
      SINGLE_ITEM_TIMEOUT_MS
    )
  );

  const result = await Promise.race([uploadPromise, timeoutPromise]);
  const duration = Date.now() - startTime;
  console.log(`[Sync] Confirmed ${item.package_id} in ${duration}ms`);
  return result;
}

/**
 * Syncs the queue with per-item atomic commits and timeout resilience.
 */
export async function syncOfflineQueue(onProgress) {
  const queue = await getOfflineQueue();
  const totalCount = queue.length;

  if (totalCount === 0) {
    return { syncedCount: 0, remainingCount: 0 };
  }

  console.log(`[Sync] Starting batch sync for ${totalCount} queued records`);
  const baseUrl = apiClient.BASE_URL || 'http://192.168.12.196:8000';
  let syncedCount = 0;

  for (const item of queue) {
    try {
      await uploadQueuedItemWithTimeout(item, baseUrl);
      await removeQueueItemById(item.id);
      syncedCount++;

      if (typeof onProgress === 'function') {
        onProgress(syncedCount, totalCount);
      }

      await new Promise((res) => setTimeout(res, 50));
    } catch (err) {
      console.warn(`[Sync Abort] Failed for package ${item.package_id}: ${err.message}`);
      if (err.message.includes('timeout') || err.message.includes('Network request failed') || err.message.includes('Failed to connect')) {
        console.warn('[Sync] Network unreachable or timed out. Halting queue sync to preserve state.');
        break;
      }
    }
  }

  const remaining = await getOfflineQueue();
  console.log(`[Sync] Run ended. Synced: ${syncedCount}, Remaining: ${remaining.length}`);
  return {
    syncedCount,
    remainingCount: remaining.length,
    totalCount,
  };
}