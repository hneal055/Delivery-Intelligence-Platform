import { useEffect, useRef, useState } from 'react';
import * as Location from 'expo-location';
import { useAuthStore } from '../stores/authStore';
import { WS_URL } from '../api/client';

export function useTracking() {
  const driverId = useAuthStore((s) => s.driverId);
  const token = useAuthStore((s) => s.token);
  const [status, setStatus] = useState('disconnected'); // disconnected, connecting, connected
  const ws = useRef(null);
  const locationSub = useRef(null);

  useEffect(() => {
    if (!token || !driverId) return;

    let unmounted = false;

    const connect = () => {
      if (unmounted) return;
      setStatus('connecting');
      // Append token if backend requires it in query param or protocol
      // e.g. `?token=${token}`
      const url = `${WS_URL}/ws/tracking/${driverId}`;
      console.log('Connecting to WebSocket:', url);

      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        console.log('WebSocket Connected');
        setStatus('connected');
        startLocationUpdates();
      };

      ws.current.onmessage = (e) => {
        // Handle incoming messages (e.g. "Job Assigned")
        console.log('Msg received:', e.data);
      };

      ws.current.onerror = (e) => {
        console.log('WebSocket Error:', e.message);
      };

      ws.current.onclose = (e) => {
        console.log('WebSocket Closed', e.code, e.reason);
        stopLocationUpdates();
        if (!unmounted) {
          setStatus('disconnected');
          setTimeout(connect, 5000);
        }
      };
    };

    connect();

    return () => {
      unmounted = true;
      if (ws.current) {
        ws.current.close();
      }
      stopLocationUpdates();
    };
  }, [driverId, token]);

  const startLocationUpdates = async () => {
    const { status } = await Location.requestForegroundPermissionsAsync();
    if (status !== 'granted') {
      console.log('Permission to access location was denied');
      return;
    }

    locationSub.current = await Location.watchPositionAsync(
      {
        accuracy: Location.Accuracy.High,
        timeInterval: 5000, 
        distanceInterval: 10,
      },
      (loc) => {
        if (ws.current && ws.current.readyState === WebSocket.OPEN) {
          const payload = {
            latitude: loc.coords.latitude,
            longitude: loc.coords.longitude,
            timestamp: loc.timestamp,
            speed: loc.coords.speed,
            heading: loc.coords.heading
          };
          ws.current.send(JSON.stringify(payload));
        }
      }
    );
  };

  const stopLocationUpdates = () => {
    if (locationSub.current) {
      locationSub.current.remove();
      locationSub.current = null;
    }
  };

  return { status };
}
