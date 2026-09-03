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

  try {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      return {
        coords: null,
        statusText: 'GPS Permission Denied',
        isMocked: false,
      };
    }

    let coords = null;
    try {
      const lastKnown = await Location.getLastKnownPositionAsync();
      if (lastKnown) coords = lastKnown.coords;
    } catch {}

    const fresh = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });
    if (fresh) coords = fresh.coords;

    return {
      coords,
      statusText: coords
        ? `Live GPS (±${Math.round(coords.accuracy || 0)}m)`
        : 'GPS Fix Unavailable',
      isMocked: false,
    };
  } catch (err) {
    return {
      coords: null,
      statusText: 'GPS Error',
      isMocked: false,
    };
  }
}