import { Marker, Popup } from "react-leaflet";
import L from "leaflet";
import type { Driver } from "../../types";

interface DriverMarkerProps {
  driver: Driver;
  lat: number;
  lon: number;
  isSelected?: boolean;
  onClick?: () => void;
}

function createDriverIcon(isOnline: boolean, isSelected: boolean) {
  const color = isSelected ? "#228be6" : isOnline ? "#40c057" : "#868e96";
  const size = isSelected ? 14 : 10;

  return L.divIcon({
    className: "driver-marker",
    html: `<div style="
      width: ${size}px;
      height: ${size}px;
      border-radius: 50%;
      background: ${color};
      border: 2px solid white;
      box-shadow: 0 1px 4px rgba(0,0,0,0.3);
    "></div>`,
    iconSize: [size + 4, size + 4],
    iconAnchor: [(size + 4) / 2, (size + 4) / 2],
  });
}

export function DriverMarker({ driver, lat, lon, isSelected, onClick }: DriverMarkerProps) {
  return (
    <Marker
      position={[lat, lon]}
      icon={createDriverIcon(driver.is_online, !!isSelected)}
      eventHandlers={{
        click: () => onClick?.(),
      }}
    >
      <Popup>
        <div>
          <strong>{driver.name}</strong>
          <br />
          Status: {driver.status}
          <br />
          Packages: {driver.package_count}
          <br />
          <small>
            {lat.toFixed(4)}, {lon.toFixed(4)}
          </small>
        </div>
      </Popup>
    </Marker>
  );
}
