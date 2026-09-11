import { BASE_URL } from '../api/client';

/**
 * Manages offline sync queue for uploading pending delivery proof records when network is available.
 */
export async function processOfflineQueue(storageClient) {
  try {
    const pendingRecords = await storageClient.getPendingRecords();
    if (!pendingRecords || pendingRecords.length === 0) {
      return { synced: 0, remaining: 0 };
    }

    let syncedCount = 0;
    for (const record of pendingRecords) {
      try {
        const response = await fetch(`${BASE_URL}/delivery/confirm`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(record.payload),
        });

        if (response.ok) {
          await storageClient.markAsSynced(record.id);
          syncedCount++;
        } else {
          console.warn(`[Sync Abort] Failed for record ${record.id}: Server status ${response.status}`);
          break; // Halt batch on first server failure
        }
      } catch (networkError) {
        console.warn(`[Sync Abort] Network error for record ${record.id}: ${networkError.message}`);
        break; // Halt batch on network failure
      }
    }

    const remainingRecords = await storageClient.getPendingRecords();
    return { synced: syncedCount, remaining: remainingRecords.length };
  } catch (error) {
    console.error('[Sync Error] Failed processing offline queue:', error);
    throw error;
  }
}