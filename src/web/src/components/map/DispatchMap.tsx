import { MapContainer, TileLayer } from "react-leaflet";
import { DriverMarker } from "./DriverMarker";
import { DriverHistory } from "./DriverHistory";
import { useRealtimeStore } from "../../stores/realtimeStore";
import type { Driver } from "../../types";
import "leaflet/dist/leaflet.css";

interface DispatchMapProps {
  drivers: Driver[];
  selectedDriverId?: string | null;
  onSelectDriver?: (driverId: string) => void;
}

export function DispatchMap({ drivers, selectedDriverId, onSelectDriver }: DispatchMapProps) {
  const realtimeLocations = useRealtimeStore((s) => s.driverLocations);

  // Merge API driver data with real-time WebSocket locations
  const driverMarkers = drivers
    .map((driver) => {
      const rtLoc = realtimeLocations[driver.id];
      const lat = rtLoc?.lat ?? driver.current_lat;
      const lon = rtLoc?.lon ?? driver.current_lon;
      if (lat == null || lon == null) return null;
      return { driver, lat, lon };
    })
    .filter(Boolean) as { driver: Driver; lat: number; lon: number }[];

  // Default center: Chicago area (matches fleet simulator)
  const center: [number, number] = driverMarkers.length > 0
    ? [
        driverMarkers.reduce((sum, m) => sum + m.lat, 0) / driverMarkers.length,
        driverMarkers.reduce((sum, m) => sum + m.lon, 0) / driverMarkers.length,
      ]
    : [41.8781, -87.6298];

  return (
    <MapContainer
      center={center}
      zoom={12}
      style={{ height: "100%", width: "100%", minHeight: "400px", borderRadius: "8px" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      
      {selectedDriverId && <DriverHistory driverId={selectedDriverId} />}

      {driverMarkers.map(({ driver, lat, lon }) => (
        <DriverMarker
          key={driver.id}
          driver={driver}
          lat={lat}
          lon={lon}
          isSelected={selectedDriverId === driver.id}
          onClick={() => onSelectDriver?.(driver.id)}
        />
      ))}
    </MapContainer>
  );
}
