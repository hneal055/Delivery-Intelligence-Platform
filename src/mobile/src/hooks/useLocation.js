import { useEffect, useRef } from 'react';
import { Alert, Platform } from 'react-native';
import * as Location from 'expo-location';
import { useLocationStore } from '../stores/locationStore';

export function useLocation() {
  const setLocation = useLocationStore((s) => s.setLocation);
  const setError = useLocationStore((s) => s.setError);
  const location = useLocationStore((s) => s.location);
  const errorMsg = useLocationStore((s) => s.errorMsg);
  const subscriptionRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();

      if (status !== 'granted') {
        const msg = 'Location permission is required to verify deliveries and calculate ETAs.';
        setError(msg);
        if (Platform.OS !== 'web') {
          Alert.alert(
            'Location Required',
            msg,
            [{ text: 'OK' }]
          );
        }
        return;
      }

      if (cancelled) return;

      // BestForNavigation gives the highest accuracy available on iPhone 17's GPS chip.
      // The distance filter (15m) avoids redundant updates while driving between stops.
      subscriptionRef.current = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.BestForNavigation,
          timeInterval: 5000,
          distanceInterval: 15,
        },
        (newLoc) => {
          if (!cancelled) {
            setLocation(newLoc);
          }
        }
      );
    })();

    return () => {
      cancelled = true;
      if (subscriptionRef.current) {
        subscriptionRef.current.remove();
        subscriptionRef.current = null;
      }
    };
  }, [setLocation, setError]);

  return { location, errorMsg };
}
