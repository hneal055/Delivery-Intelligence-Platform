import { Marker, Polyline } from "react-leaflet";
import L from "leaflet";

interface RoutePlaybackProps {
  positions: [number, number][];
  currentIndex: number;
}

const playbackIcon = L.divIcon({
  className: "playback-marker",
  html: `<div style="
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #e64980;
    border: 3px solid white;
    box-shadow: 0 2px 6px rgba(0,0,0,0.4);
  "></div>`,
  iconSize: [22, 22],
  iconAnchor: [11, 11],
});

export function RoutePlayback({ positions, currentIndex }: RoutePlaybackProps) {
  if (positions.length < 2) return null;

  const traveled = positions.slice(0, currentIndex + 1);
  const remaining = positions.slice(currentIndex);
  const currentPos = positions[currentIndex];

  return (
    <>
      {traveled.length >= 2 && (
        <Polyline positions={traveled} color="#228be6" weight={4} opacity={0.8} />
      )}
      {remaining.length >= 2 && (
        <Polyline positions={remaining} color="#868e96" weight={3} opacity={0.4} dashArray="8 6" />
      )}
      {currentPos && <Marker position={currentPos} icon={playbackIcon} />}
    </>
  );
}
