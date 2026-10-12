import { Marker, Popup, Tooltip } from "react-leaflet";
import L from "leaflet";
import type { Driver } from "../../types";
import { useRealtimeStore } from "../../stores/realtimeStore";

interface DriverMarkerProps {
  driver: Driver;
  lat: number;
  lon: number;
  isSelected?: boolean;
  onClick?: () => void;
}

// A position older than this is shown grey, so an old dot never looks live.
const STALE_MS = 5 * 60 * 1000;

/** The API sends UTC times without a zone ("2026-10-12T13:05:01"). */
function parseUtc(value: string | null): number | null {
  if (!value) return null;
  const hasZone = /(Z|[+-]\d{2}:?\d{2})$/.test(value);
  const ms = Date.parse(hasZone ? value : `${value}Z`);
  return Number.isNaN(ms) ? null : ms;
}

function lastSeenText(seenMs: number | null): string {
  if (seenMs == null) return "Last seen: unknown";
  const minutes = Math.floor((Date.now() - seenMs) / 60000);
  if (minutes < 1) return "Last seen just now";
  if (minutes < 60) return `Last seen ${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `Last seen ${hours} h ago`;
  return `Last seen ${new Date(seenMs).toLocaleString()}`;
}

function createDriverIcon(isLive: boolean, isSelected: boolean) {
  const color = isSelected ? "#228be6" : isLive ? "#40c057" : "#868e96";
  const size = isSelected ? 18 : 13;

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
  // Latest of the live update (seconds) and the last saved position.
  const liveTs = useRealtimeStore((s) => s.driverLocations[driver.id]?.timestamp);
  const savedMs = parseUtc(driver.last_updated);
  const liveMs = liveTs != null ? liveTs * 1000 : null;
  const seenMs = liveMs != null && (savedMs == null || liveMs > savedMs) ? liveMs : savedMs;
  const isLive = seenMs != null && Date.now() - seenMs < STALE_MS;

  return (
    <Marker
      position={[lat, lon]}
      icon={createDriverIcon(isLive, !!isSelected)}
      eventHandlers={{
        click: () => onClick?.(),
      }}
    >
      <Tooltip permanent direction="right" offset={[10, 0]} opacity={0.9}>
        {driver.name}
      </Tooltip>
      <Popup>
        <div>
          <strong>{driver.name}</strong>
          <br />
          {lastSeenText(seenMs)}
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
