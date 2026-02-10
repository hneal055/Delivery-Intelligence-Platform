import { useEffect, useState } from 'react';
import { Polyline } from 'react-leaflet';
import { useQuery } from '@tanstack/react-query';
import { getLocationHistory } from '../../api/dispatch';

interface DriverHistoryProps {
  driverId: string;
}

export function DriverHistory({ driverId }: DriverHistoryProps) {
  const { data: locations = [] } = useQuery({
    queryKey: ['locationHistory', driverId],
    queryFn: () => getLocationHistory(driverId, 24), // Last 24 hours
    enabled: !!driverId,
  });

  const path = locations.map(l => [l.lat, l.lon] as [number, number]);

  if (path.length < 2) return null;

  return <Polyline positions={path} color="blue" weight={4} opacity={0.6} />;
}
