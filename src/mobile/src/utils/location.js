import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Location from 'expo-location';

const DEV_MOCK_GPS_KEY = '@dev_mock_chicago_gps';

// Chicago Loop Depot default coordinates
export const CHICAGO_DEPOT = {
  latitude: 41.881837,
  longitude: -87.632420,
  accuracy: 5,
};

// In-memory cache to prevent race conditions during renders
let memoryCache = false;

export async function isDevMockGpsEnabled() {
  try {
    const val = await AsyncStorage.getItem(DEV_MOCK_GPS_KEY);
    memoryCache = val === 'true';
    return memoryCache;
  } catch {
    return memoryCache;
  }
}

export async function updateDevMockGps(enabled) {
  memoryCache = Boolean(enabled);
  try {
    await AsyncStorage.setItem(DEV_MOCK_GPS_KEY, enabled ? 'true' : 'false');
  } catch (err) {
    console.error('Failed to set dev mock GPS in storage:', err);
  }
  return memoryCache;
}

/**
 * Resolves current GPS coordinates, respecting the Chicago Dev Mode toggle.
 */
export async function getEffectiveLocation() {
  const isMocked = await isDevMockGpsEnabled();
  if (isMocked) {
    return {
      coords: CHICAGO_DEPOT,
      statusText: 'Chicago Sim (Dev Mode)',
      isMocked: true,
    };
  }

  let status;
  try {
    ({ status } = await Location.requestForegroundPermissionsAsync());
  } catch (err) {
    return { coords: null, statusText: `GPS Error: ${err.message}`, isMocked: false };
  }
  if (status !== 'granted') {
    return { coords: null, statusText: 'GPS Permission Denied', isMocked: false };
  }

  // A fresh, accurate fix is preferred; if it fails or is slow, a recent
  // last-known position is still a truthful record of where the phone was.
  let lastKnown = null;
  try {
    lastKnown = await Location.getLastKnownPositionAsync({ maxAge: LAST_KNOWN_MAX_AGE_MS });
  } catch {}

  try {
    const fresh = await withTimeout(
      Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High }),
      FRESH_FIX_TIMEOUT_MS
    );
    return {
      coords: fresh.coords,
      statusText: `Live GPS (±${Math.round(fresh.coords.accuracy || 0)}m)`,
      isMocked: false,
    };
  } catch (err) {
    if (lastKnown) {
      return {
        coords: lastKnown.coords,
        statusText: `Last known GPS (±${Math.round(lastKnown.coords.accuracy || 0)}m)`,
        isMocked: false,
      };
    }
    return { coords: null, statusText: `GPS Error: ${err.message}`, isMocked: false };
  }
}

const FRESH_FIX_TIMEOUT_MS = 10000;
const LAST_KNOWN_MAX_AGE_MS = 2 * 60 * 1000;

function withTimeout(promise, ms) {
  let timer;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`no fix within ${ms / 1000}s`)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => clearTimeout(timer));
}