import { useEffect, useRef, useState } from 'react';
import { AppState } from 'react-native';
import * as Location from 'expo-location';
import { useAuthStore } from '../stores/authStore';
import { useLocationStore } from '../stores/locationStore';
import { WS_URL } from '../api/client';

const BASE_RETRY_DELAY_MS = 2000;
const MAX_RETRY_DELAY_MS = 60000;
const MAX_RETRIES = 10;

export function useTracking() {
  const driverId = useAuthStore((s) => s.driverId);
  const token = useAuthStore((s) => s.token);
  const setLocation = useLocationStore((s) => s.setLocation);
  const [status, setStatus] = useState('disconnected');

  const ws = useRef(null);
  const locationSub = useRef(null);
  const retryCount = useRef(0);
  const retryTimer = useRef(null);
  const unmounted = useRef(false);
  const appState = useRef(AppState.currentState);

  useEffect(() => {
    if (!token || !driverId) {
      setStatus('no-auth');
      return;
    }

    unmounted.current = false;

    connect();

    const appStateSub = AppState.addEventListener('change', (nextState) => {
      if (appState.current.match(/inactive|background/) && nextState === 'active') {
        if (!ws.current || ws.current.readyState === WebSocket.CLOSED) {
          retryCount.current = 0;
          connect();
        }
      } else if (nextState.match(/inactive|background/)) {
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
    };
  }, [driverId, token]);

  function connect() {
    if (unmounted.current) return;
    if (retryCount.current >= MAX_RETRIES) {
      setStatus('failed');
      return;
    }

    setStatus('connecting');
    // Use correct backend endpoint: /ws/driver/{driver_id} with token query param
    const url = `${WS_URL}/ws/driver/${driverId}?token=${encodeURIComponent(token)}`;

    try {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        retryCount.current = 0;
        setStatus('connected');
        startLocationUpdates();
      };

      ws.current.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          console.log('Tracking message:', msg);
          // Handle dispatcher messages (job assignments, route updates, alerts)
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
    if (permStatus !== 'granted') return;

    locationSub.current = await Location.watchPositionAsync(
      {
        accuracy: Location.Accuracy.BestForNavigation,
        timeInterval: 5000,
        distanceInterval: 15,
      },
      (loc) => {
        // Update Zustand store so DeliveryDetailScreen can use it
        setLocation(loc);

        // Send to backend WebSocket using correct message format
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
          const speedKmh = loc.coords.speed ? loc.coords.speed * 3.6 : 0;
          ws.current.send(JSON.stringify({
            type: 'location_update',
            lat: loc.coords.latitude,
            lon: loc.coords.longitude,
            speed_kmh: speedKmh,
            heading: loc.coords.heading || 0,
            timestamp: loc.timestamp,
          }));
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

  return { status };
}
