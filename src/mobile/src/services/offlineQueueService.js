import * as SQLite from "expo-sqlite";
import { Platform } from "react-native";
import client from "../api/client";

const DB_NAME = "offline_deliveries.db";
let db = null;
let initPromise = null;

/**
 * Initialize SQLite database and pending deliveries table.
 * Includes column migration for photo_uri if upgrading existing database.
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
 * Enqueue a confirmed delivery record into SQLite (supports optional photoUri)
 */
export async function queueDeliveryConfirmation({
  packageId,
  driverId,
  lat = 41.8786,
  lon = -87.6403,
  signaturePath = "",
  photoUri = null,
}) {
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
        String(driverId || "D001"),
        lat,
        lon,
        signaturePath,
        photoUri || null,
        timestamp,
      ]
    );

    console.log(`[OfflineDB] Enqueued delivery for ${packageId}`);
    return true;
  } catch (err) {
    console.error(`[OfflineDB] Error enqueuing ${packageId}:`, err);
    return false;
  }
}

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
 * Drain and flush queued records to the backend.
 * Uses native fetch to bypass Axios multipart/form-data boundary issues on Android.
 * Attaches captured photo proof when available.
 * Prunes poison pill 4xx records so failed validations do not cause infinite loops.
 */
export async function processOfflineQueue() {
  if (Platform.OS === "web") return { syncedCount: 0 };

  try {
    const database = await initOfflineDatabase();
    if (!database) return { syncedCount: 0 };

    const pending = await database.getAllAsync(
      "SELECT * FROM pending_deliveries WHERE status = 'PENDING' ORDER BY id ASC LIMIT 10"
    );

    if (!pending || pending.length === 0) {
      return { syncedCount: 0 };
    }

    let syncedCount = 0;
    const baseUrl = client?.defaults?.baseURL || "http://localhost:8000";

    for (const record of pending) {
      try {
        const formData = new FormData();
        formData.append("package_id", String(record.package_id));
        formData.append("driver_id", String(record.driver_id || "D001"));
        formData.append("dest_lat", String(record.lat ?? "41.8786"));
        formData.append("dest_lon", String(record.lon ?? "-87.6403"));
        formData.append("signature_path", record.signature_path || "OFFLINE_CAPTURE");

        // Attach photo file payload if a URI is saved
        if (record.photo_uri) {
          const rawUri = record.photo_uri;
          const fileName = rawUri.split("/").pop() || `delivery_${record.package_id}.jpg`;
          formData.append("photo", {
            uri: rawUri,
            name: fileName,
            type: "image/jpeg",
          });
        }

        // Native fetch lets the runtime generate correct multipart boundary headers
        const response = await fetch(`${baseUrl}/delivery/confirm`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const errorText = await response.text();
          const err = new Error(`Request failed with status code ${response.status}: ${errorText}`);
          err.response = { status: response.status, data: errorText };
          throw err;
        }

        // Delete processed record upon successful 200 OK
        await database.runAsync("DELETE FROM pending_deliveries WHERE id = ?", [record.id]);
        syncedCount++;
        console.log(`[OfflineDB] Successfully synced & purged record #${record.id} (${record.package_id})`);
      } catch (err) {
        const statusCode = err.response?.status;
        console.warn(`[OfflineDB] Sync failed for record #${record.id} (${record.package_id}): ${err.message}`);

        if (statusCode >= 400 && statusCode < 500) {
          // 4xx client/validation error: mark FAILED so it won't loop
          console.error(`[OfflineDB] Client error (${statusCode}) for record #${record.id}. Marking FAILED.`);
          await database.runAsync(
            "UPDATE pending_deliveries SET status = 'FAILED', attempts = attempts + 1 WHERE id = ?",
            [record.id]
          );
        } else {
          // Network issue or 5xx server error: increment retry count
          await database.runAsync(
            "UPDATE pending_deliveries SET attempts = attempts + 1 WHERE id = ?",
            [record.id]
          );
        }
      }
    }

    return { syncedCount };
  } catch (err) {
    console.error("[OfflineDB] Critical error processing offline queue:", err);
    return { syncedCount: 0 };
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
