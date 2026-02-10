import { useEffect } from 'react';
import * as Location from 'expo-location';
import { useLocationStore } from '../stores/locationStore';

export function useLocation() {
  const setLocation = useLocationStore((s) => s.setLocation);
  const setError = useLocationStore((s) => s.setError);
  const location = useLocationStore((s) => s.location);
  const errorMsg = useLocationStore((s) => s.errorMsg);

  useEffect(() => {
    let subscription;

    (async () => {
      const { status } = await Location.requestForegroundPermissionsAsync();
      if (status !== 'granted') {
        setError('Permission to access location was denied');
        return;
      }

      subscription = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          timeInterval: 5000,
          distanceInterval: 10,
        },
        (newLoc) => {
          setLocation(newLoc);
        }
      );
    })();

    return () => {
      if (subscription) {
        subscription.remove();
      }
    };
  }, [setLocation, setError]);

  return { location, errorMsg };
}
