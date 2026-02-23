import { useEffect, useRef, useState } from 'react';
import { AppState, Platform } from 'react-native';
import * as Location from 'expo-location';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useAuthStore } from '../stores/authStore';
import { useLocationStore } from '../stores/locationStore';
import { WS_URL } from '../api/client';

const BASE_RETRY_DELAY_MS = 2000;
const MAX_RETRY_DELAY_MS = 60000;
const MAX_RETRIES = 10;
const OFFLINE_QUEUE_KEY = 'location_updates_queue';
const PERMISSION_ERROR_KEY = 'gps_permission_error';

export function useTracking() {
  const driverId = useAuthStore((s) => s.driverId);
  const token = useAuthStore((s) => s.token);
  const refreshTokenIfNeeded = useAuthStore((s) => s.refreshTokenIfNeeded);
  const setLocation = useLocationStore((s) => s.setLocation);
  const [status, setStatus] = useState('disconnected');
  const [permissionStatus, setPermissionStatus] = useState('unknown');

  const ws = useRef(null);
  const locationSub = useRef(null);
  const retryCount = useRef(0);
  const retryTimer = useRef(null);
  const unmounted = useRef(false);
  const appState = useRef(AppState.currentState);
  const pendingLocationUpdates = useRef([]);
  const offlineQueueTimer = useRef(null);

  // Check and request location permissions (iOS requires foreground + background)
  async function requestLocationPermissions() {
    try {
      // First request foreground permission
      const foregroundStatus = await Location.requestForegroundPermissionsAsync();
      
      if (foregroundStatus.status !== 'granted') {
        setPermissionStatus('denied');
        await AsyncStorage.setItem(PERMISSION_ERROR_KEY, 'User denied foreground location permission');
        return false;
      }

      setPermissionStatus('foreground-granted');

      // iOS requires separate background location permission
      if (Platform.OS === 'ios') {
        const backgroundStatus = await Location.requestBackgroundPermissionsAsync();
        if (backgroundStatus.status === 'granted') {
          setPermissionStatus('granted');
        } else {
          // Foreground works, background is just a "nice to have"
          console.warn('Background location not granted on iOS, but foreground works');
          setPermissionStatus('foreground-only');
        }
      } else {
        // Android foreground permission is sufficient
        setPermissionStatus('granted');
      }

      return true;
    } catch (error) {
      console.error('Permission request failed:', error);
      setPermissionStatus('error');
      await AsyncStorage.setItem(PERMISSION_ERROR_KEY, error.message);
      return false;
    }
  }

  // Restore queued locations from AsyncStorage and send them to WebSocket
  async function processOfflineQueue() {
    if (!ws.current || ws.current.readyState !== WebSocket.OPEN) return;

    try {
      const queueJson = await AsyncStorage.getItem(OFFLINE_QUEUE_KEY);
      if (!queueJson) return;

      const queue = JSON.parse(queueJson);
      if (queue.length === 0) return;

      console.log(`Processing ${queue.length} queued location updates`);

      for (const update of queue) {
        ws.current.send(JSON.stringify(update));
      }

      // Clear queue after sending
      await AsyncStorage.removeItem(OFFLINE_QUEUE_KEY);
      pendingLocationUpdates.current = [];
    } catch (error) {
      console.error('Error processing offline queue:', error);
    }
  }

  // Save location update to offline queue in AsyncStorage
  async function queueLocationUpdate(update) {
    try {
      const queueJson = await AsyncStorage.getItem(OFFLINE_QUEUE_KEY);
      const queue = queueJson ? JSON.parse(queueJson) : [];
      
      // Keep max 500 queued updates to avoid excessive storage
      if (queue.length < 500) {
        queue.push(update);
        await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queue));
      } else {
        console.warn('Location queue at max capacity (500), dropping oldest update');
        queue.shift();
        queue.push(update);
        await AsyncStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(queue));
      }
    } catch (error) {
      console.error('Failed to queue location update:', error);
    }
  }

  useEffect(() => {
    if (!token || !driverId) {
      setStatus('no-auth');
      return;
    }

    unmounted.current = false;
    init();

    const appStateSub = AppState.addEventListener('change', (nextState) => {
      if (appState.current.match(/inactive|background/) && nextState === 'active') {
        // App coming to foreground: refresh token and reconnect
        handleAppForeground();
      } else if (nextState.match(/inactive|background/)) {
        // App going to background: stop location updates
        stopLocationUpdates();
      }
      appState.current = nextState;
    });

    return () => {
      unmounted.current = true;
      appStateSub.remove();
      clearRetryTimer();
      closeSocket();
      stopLocationUpdates();
      if (offlineQueueTimer.current) clearTimeout(offlineQueueTimer.current);
    };
  }, [driverId, token]);

  async function init() {
    // Check existing permission status first
    const currentStatus = await Location.getForegroundPermissionsAsync();
    
    if (currentStatus.status !== 'granted') {
      const hasPermission = await requestLocationPermissions();
      if (!hasPermission) {
        setStatus('no-permission');
        return;
      }
    } else {
      setPermissionStatus('granted');
    }

    // Attempt connection
    connect();
  }

  async function handleAppForeground() {
    // Refresh token before reconnecting to ensure it''s valid
    const refreshed = await refreshTokenIfNeeded();
    if (!refreshed) {
      console.warn('Token refresh on foreground failed, attempting with existing token');
    }

    if (!ws.current || ws.current.readyState === WebSocket.CLOSED) {
      retryCount.current = 0;
      connect();
    }

    // Process any queued location updates
    await processOfflineQueue();
  }

  function connect() {
    if (unmounted.current) return;
    if (retryCount.current >= MAX_RETRIES) {
      setStatus('failed');
      return;
    }

    setStatus('connecting');
    const url = `${WS_URL}/ws/driver/${driverId}?token=${encodeURIComponent(token)}`;

    try {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        retryCount.current = 0;
        setStatus('connected');
        startLocationUpdates();
        // Process any offline queue when connection re-established
        processOfflineQueue();
      };

      ws.current.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          console.log('Tracking message:', msg);
        } catch {
          console.log('Tracking raw message:', e.data);
        }
      };

      ws.current.onerror = (e) => {
        console.warn('WebSocket error:', e.message || 'Connection failed');
      };

      ws.current.onclose = (e) => {
        stopLocationUpdates();
        if (!unmounted.current && appState.current === 'active') {
          setStatus('disconnected');
          scheduleRetry();
        }
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
      setStatus('error');
      scheduleRetry();
    }
  }

  function scheduleRetry() {
    retryCount.current += 1;
    const delay = Math.min(
      BASE_RETRY_DELAY_MS * Math.pow(2, retryCount.current - 1),
      MAX_RETRY_DELAY_MS
    );
    retryTimer.current = setTimeout(connect, delay);
  }

  function clearRetryTimer() {
    if (retryTimer.current) {
      clearTimeout(retryTimer.current);
      retryTimer.current = null;
    }
  }

  function closeSocket() {
    if (ws.current) {
      ws.current.onclose = null;
      ws.current.close();
      ws.current = null;
    }
  }

  async function startLocationUpdates() {
    const { status: permStatus } = await Location.requestForegroundPermissionsAsync();
    if (permStatus !== 'granted') {
      setPermissionStatus('denied');
      return;
    }

    locationSub.current = await Location.watchPositionAsync(
      {
        accuracy: Location.Accuracy.BestForNavigation,
        timeInterval: 5000,
        distanceInterval: 15,
      },
      async (loc) => {
        setLocation(loc);

        const speedKmh = loc.coords.speed ? loc.coords.speed * 3.6 : 0;
        const update = {
          type: 'location_update',
          lat: loc.coords.latitude,
          lon: loc.coords.longitude,
          speed_kmh: speedKmh,
          heading: loc.coords.heading || 0,
          timestamp: loc.timestamp,
        };

        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
          // Send immediately if connected
          ws.current.send(JSON.stringify(update));
        } else {
          // Queue for later if offline
          await queueLocationUpdate(update);
        }
      }
    );
  }

  function stopLocationUpdates() {
    if (locationSub.current) {
      locationSub.current.remove();
      locationSub.current = null;
    }
  }

  return { status, permissionStatus };
}

