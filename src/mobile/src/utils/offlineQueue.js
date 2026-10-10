import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system/legacy';
import * as ImageManipulator from 'expo-image-manipulator';
import { BASE_URL, authHeaders } from '../api/client';

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
 * Multipart form fields for POST /delivery/confirm. GPS and signature are
 * only sent when present, never as placeholder values.
 */
export function buildConfirmFields(item) {
  const fields = {
    package_id: String(item.package_id),
    driver_id: String(item.driver_id),
  };
  if (item.dest_lat != null && item.dest_lon != null) {
    fields.dest_lat = String(item.dest_lat);
    fields.dest_lon = String(item.dest_lon);
  }
  if (item.signature_path) {
    fields.signature_path = item.signature_path;
  }
  return fields;
}

/**
 * Upload one proof of delivery. Resolves with the parsed response body;
 * rejects with err.status set for HTTP errors (no status = network failure).
 */
export async function uploadConfirmation(item, photoUri) {
  const response = await FileSystem.uploadAsync(`${BASE_URL}/delivery/confirm`, photoUri, {
    fieldName: 'photo',
    httpMethod: 'POST',
    uploadType: FileSystem.FileSystemUploadType.MULTIPART,
    headers: authHeaders(),
    parameters: buildConfirmFields(item),
  });

  if (response.status < 200 || response.status >= 300) {
    let detail = `Server returned ${response.status}`;
    try {
      detail = JSON.parse(response.body).detail || detail;
    } catch {}
    const err = new Error(detail);
    err.status = response.status;
    throw err;
  }
  return JSON.parse(response.body);
}

/**
 * Enqueues a delivery item to AsyncStorage.
 */
export async function enqueueOfflineDelivery(payload) {
  if (!payload.photoUri) {
    throw new Error('A proof photo is required to queue a delivery.');
  }
  try {
    const existing = await getOfflineQueue();
    const permanentPhotoUri = await compressAndPreservePhoto(payload.photoUri, payload.package_id);

    const queueItem = {
      id: `queue_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`,
      timestamp: new Date().toISOString(),
      package_id: payload.package_id,
      driver_id: payload.driver_id,
      dest_lat: payload.dest_lat ?? null,
      dest_lon: payload.dest_lon ?? null,
      signature_path: payload.signature_path || '',
      photoUri: permanentPhotoUri,
      retryCount: 0,
      failed: false,
      lastError: null,
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

async function saveQueue(queue) {
  await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queue));
}

/**
 * Removes a specific single item from the queue immediately after success.
 */
async function removeQueueItemById(itemId) {
  try {
    const queue = await getOfflineQueue();
    await saveQueue(queue.filter((i) => i.id !== itemId));
  } catch (err) {
    console.error('[OfflineQueue] Failed to prune queue item:', err);
  }
}

/**
 * The server refused this item (e.g. unknown package, photo rejected). Keep
 * it -- it is evidence -- but stop retrying it automatically.
 */
async function markQueueItemFailed(itemId, message) {
  const queue = await getOfflineQueue();
  await saveQueue(
    queue.map((i) =>
      i.id === itemId
        ? { ...i, failed: true, lastError: message, retryCount: (i.retryCount || 0) + 1 }
        : i
    )
  );
}

/**
 * Uploads a single queued record with timeout safeguard and console timing.
 */
async function uploadQueuedItemWithTimeout(item) {
  const startTime = Date.now();
  console.log(`[Sync] Uploading ${item.package_id}... (12s timeout armed)`);

  let timer;
  const timeoutPromise = new Promise((_, reject) => {
    timer = setTimeout(
      () => reject(new Error(`Upload timeout after ${SINGLE_ITEM_TIMEOUT_MS / 1000}s`)),
      SINGLE_ITEM_TIMEOUT_MS
    );
  });

  try {
    const result = await Promise.race([uploadConfirmation(item, item.photoUri), timeoutPromise]);
    try {
      await FileSystem.deleteAsync(item.photoUri, { idempotent: true });
    } catch {}
    console.log(`[Sync] Confirmed ${item.package_id} in ${Date.now() - startTime}ms`);
    return result;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Syncs the queue with per-item atomic commits and timeout resilience.
 * Network failures and 401 (login needed) stop the run and keep everything;
 * other 4xx responses mark that item failed; 5xx is retried next run.
 */
export async function syncOfflineQueue(onProgress) {
  const queue = (await getOfflineQueue()).filter((i) => !i.failed);
  const totalCount = queue.length;

  if (totalCount === 0) {
    const all = await getOfflineQueue();
    return { syncedCount: 0, remainingCount: all.length, totalCount: 0 };
  }

  console.log(`[Sync] Starting batch sync for ${totalCount} queued records`);
  let syncedCount = 0;

  for (const item of queue) {
    try {
      await uploadQueuedItemWithTimeout(item);
      await removeQueueItemById(item.id);
      syncedCount++;

      if (typeof onProgress === 'function') {
        onProgress(syncedCount, totalCount);
      }

      await new Promise((res) => setTimeout(res, 50));
    } catch (err) {
      console.warn(`[Sync] Failed for package ${item.package_id}: ${err.message}`);
      if (!err.status || err.status === 401) {
        console.warn('[Sync] Offline or logged out. Halting queue sync to preserve state.');
        break;
      }
      if (err.status >= 400 && err.status < 500) {
        await markQueueItemFailed(item.id, err.message);
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
