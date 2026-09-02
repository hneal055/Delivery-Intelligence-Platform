import * as SQLite from "expo-sqlite";
import { Platform } from "react-native";
import client from "../api/client";

const DB_NAME = "offline_deliveries.db";
let db = null;
let initPromise = null;

/**
 * Initialize SQLite database and pending deliveries table.
 * Includes column migration for photo_uri if upgrading an existing database.
 */
export async function initOfflineDatabase() {
  if (Platform.OS === "web") {
    console.log("[OfflineDB] Running on Web - SQLite skipped.");
    return null;
  }

  if (db) return db;

  if (!initPromise) {
    initPromise = (async () => {
      try {
        const database = await SQLite.openDatabaseAsync(DB_NAME);

        // Ensure base table exists
        await database.execAsync(`
          CREATE TABLE IF NOT EXISTS pending_deliveries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            package_id TEXT NOT NULL,
            driver_id TEXT NOT NULL,
            lat REAL,
            lon REAL,
            signature_path TEXT,
            photo_uri TEXT,
            attempts INTEGER DEFAULT 0,
            status TEXT DEFAULT 'PENDING',
            created_at TEXT NOT NULL
          );
        `);

        // Handle migration gracefully if table existed before photo_uri was added
        try {
          await database.execAsync(`ALTER TABLE pending_deliveries ADD COLUMN photo_uri TEXT;`);
        } catch (_) {
          // Column already exists, safe to ignore
        }

        console.log("[OfflineDB] SQLite pending_deliveries table initialized successfully.");
        db = database;
        return db;
      } catch (err) {
        console.error("[OfflineDB] Failed to initialize SQLite database:", err);
        initPromise = null;
        return null;
      }
    })();
  }

  return initPromise;
}

/**
 * Enqueue a confirmed delivery record into SQLite.
 * Accepts both camelCase and snake_case properties for compatibility across all screens.
 */
export async function queueDeliveryConfirmation(payload = {}) {
  const packageId = payload.packageId || payload.package_id;
  const driverId = payload.driverId || payload.driver_id || "D001";
  const lat = payload.lat ?? payload.latitude ?? 41.8786;
  const lon = payload.lon ?? payload.longitude ?? -87.6403;
  const signaturePath = payload.signaturePath || payload.signature_path || payload.signature_data || "";
  const photoUri = payload.photoUri || payload.photo_uri || null;

  if (!packageId) return false;

  if (Platform.OS === "web") {
    console.log(`[OfflineDB:Web] Queued mock delivery for ${packageId}`);
    return true;
  }

  try {
    const database = await initOfflineDatabase();
    if (!database) return false;

    const timestamp = new Date().toISOString();
    await database.runAsync(
      `INSERT INTO pending_deliveries (package_id, driver_id, lat, lon, signature_path, photo_uri, attempts, status, created_at)
       VALUES (?, ?, ?, ?, ?, ?, 0, 'PENDING', ?)`,
      [
        String(packageId),
        String(driverId),
        lat,
        lon,
        signaturePath,
        photoUri,
        timestamp,
      ]
    );

    console.log(`[OfflineDB] Enqueued offline delivery for ${packageId}`);
    return true;
  } catch (err) {
    console.error(`[OfflineDB] Error enqueuing ${packageId}:`, err);
    return false;
  }
}

// Alias for backwards compatibility with ScannerScreen and earlier imports
export const enqueueDeliveryProof = queueDeliveryConfirmation;

/**
 * Retrieve count of active pending records in the queue
 */
export async function getPendingQueueCount() {
  if (Platform.OS === "web") return 0;

  try {
    const database = await initOfflineDatabase();
    if (!database) return 0;

    const result = await database.getFirstAsync(
      "SELECT COUNT(*) as count FROM pending_deliveries WHERE status = 'PENDING'"
    );
    return result?.count || 0;
  } catch (err) {
    console.error("[OfflineDB] Error getting pending queue count:", err);
    return 0;
  }
}

/**
 * Drain and flush queued records to the FastAPI backend.
 * Uses native fetch for correct multipart boundary handling.
 * Prunes poison-pill 4xx errors to prevent endless retry loops.
 */
export async function processOfflineQueue() {
  if (Platform.OS === "web") {
    return { syncedCount: 0, failedCount: 0, remaining: 0 };
  }

  try {
    const database = await initOfflineDatabase();
    if (!database) {
      return { syncedCount: 0, failedCount: 0, remaining: 0 };
    }

    const pending = await database.getAllAsync(
      "SELECT * FROM pending_deliveries WHERE status = 'PENDING' ORDER BY id ASC LIMIT 10"
    );

    if (!pending || pending.length === 0) {
      return { syncedCount: 0, failedCount: 0, remaining: 0 };
    }

    let syncedCount = 0;
    let failedCount = 0;
    const baseUrl = client?.defaults?.baseURL || "http://localhost:8000";

    for (const record of pending) {
      try {
        const formData = new FormData();
        formData.append("package_id", String(record.package_id));
        formData.append("driver_id", String(record.driver_id || "D001"));
        formData.append("dest_lat", String(record.lat ?? "41.8786"));
        formData.append("dest_lon", String(record.lon ?? "-87.6403"));
        formData.append("signature_path", record.signature_path || "OFFLINE_CAPTURE");

        // Re-attach local binary photo proof
        if (record.photo_uri) {
          const rawUri = record.photo_uri;
          const cleanUri = rawUri.split("?")[0];
          const fileName = cleanUri.split("/").pop() || `delivery_${record.package_id}.jpg`;

          formData.append("photo", {
            uri: rawUri,
            name: fileName,
            type: "image/jpeg",
          });
        }

        const response = await fetch(`${baseUrl}/delivery/confirm`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const errorText = await response.text();
          const err = new Error(`Request failed with status ${response.status}: ${errorText}`);
          err.status = response.status;
          throw err;
        }

        // Delete processed record upon successful upload
        await database.runAsync("DELETE FROM pending_deliveries WHERE id = ?", [record.id]);
        syncedCount++;
        console.log(`[OfflineDB] Successfully synced & purged record #${record.id} (${record.package_id})`);
      } catch (err) {
        failedCount++;
        const statusCode = err.status || err.response?.status;
        console.warn(`[OfflineDB] Sync failed for record #${record.id} (${record.package_id}):`, err.message);

        if (statusCode >= 400 && statusCode < 500) {
          // 4xx Client Validation Error -> Mark FAILED so it does not block the queue
          console.error(`[OfflineDB] 4xx Validation Error (${statusCode}) for #${record.id}. Marking FAILED.`);
          await database.runAsync(
            "UPDATE pending_deliveries SET status = 'FAILED', attempts = attempts + 1 WHERE id = ?",
            [record.id]
          );
        } else {
          // Network drop, timeout, or 5xx Server Error -> increment attempt counter
          await database.runAsync(
            "UPDATE pending_deliveries SET attempts = attempts + 1 WHERE id = ?",
            [record.id]
          );
        }
      }
    }

    const remaining = await getPendingQueueCount();

    return {
      syncedCount,
      failedCount,
      remaining,
    };
  } catch (err) {
    console.error("[OfflineDB] Critical error processing offline queue:", err);
    return { syncedCount: 0, failedCount: 0, remaining: 0 };
  }
}

/**
 * Utility: Purge all queue records
 */
export async function clearOfflineQueue() {
  if (Platform.OS === "web") return;
  try {
    const database = await initOfflineDatabase();
    if (!database) return;

    await database.runAsync("DELETE FROM pending_deliveries");
    console.log("[OfflineDB] All queue records wiped.");
  } catch (err) {
    console.error("[OfflineDB] Failed to wipe queue:", err);
  }
}

export default {
  initOfflineDatabase,
  queueDeliveryConfirmation,
  enqueueDeliveryProof,
  getPendingQueueCount,
  processOfflineQueue,
  clearOfflineQueue,
};