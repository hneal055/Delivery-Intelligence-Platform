import { useState, useCallback, useRef, useEffect } from "react";
import { Title, Container, Grid, Stack, Select, Paper, Text, Badge, Group } from "@mantine/core";
import { MapContainer, TileLayer } from "react-leaflet";
import { DriverMarker } from "../components/map/DriverMarker";
import { RoutePlayback } from "../components/map/RoutePlayback";
import { RoutePlaybackControls } from "../components/map/RoutePlaybackControls";
import { useDrivers } from "../hooks/useDrivers";
import { useLocationHistory } from "../hooks/useLocationHistory";
import { useRealtimeStore } from "../stores/realtimeStore";
import { useWebSocket } from "../hooks/useWebSocket";
import type { Driver } from "../types";
import "leaflet/dist/leaflet.css";

export function TrackingPage() {
  useWebSocket();
  const { data: drivers = [] } = useDrivers();
  const realtimeLocations = useRealtimeStore((s) => s.driverLocations);
  const [selectedDriverId, setSelectedDriverId] = useState<string | null>(null);
  const { data: history = [] } = useLocationHistory(selectedDriverId);

  // Playback state
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [speed, setSpeed] = useState("1");
  const animFrameRef = useRef<number>(0);
  const lastTickRef = useRef<number>(0);

  const historyPositions: [number, number][] = history
    .filter((p) => p.lat != null && p.lon != null)
    .map((p) => [p.lat, p.lon] as [number, number]);

  // Reset playback when driver changes
  useEffect(() => {
    setIsPlaying(false);
    setCurrentIndex(0);
  }, [selectedDriverId]);

  // Playback animation loop
  useEffect(() => {
    if (!isPlaying || historyPositions.length < 2) return;

    const interval = 500 / Number(speed); // ms per step

    const tick = (timestamp: number) => {
      if (timestamp - lastTickRef.current >= interval) {
        lastTickRef.current = timestamp;
        setCurrentIndex((prev) => {
          if (prev >= historyPositions.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }
      animFrameRef.current = requestAnimationFrame(tick);
    };

    lastTickRef.current = performance.now();
    animFrameRef.current = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(animFrameRef.current);
  }, [isPlaying, speed, historyPositions.length]);

  const handleTogglePlay = useCallback(() => {
    if (currentIndex >= historyPositions.length - 1) {
      setCurrentIndex(0);
    }
    setIsPlaying((p) => !p);
  }, [currentIndex, historyPositions.length]);

  const handleStop = useCallback(() => {
    setIsPlaying(false);
    setCurrentIndex(0);
  }, []);

  const handleSeek = useCallback((idx: number) => {
    setCurrentIndex(idx);
    setIsPlaying(false);
  }, []);

  // Build driver markers with realtime merging
  const driverMarkers = drivers
    .map((driver) => {
      const rtLoc = realtimeLocations[driver.id];
      const lat = rtLoc?.lat ?? driver.current_lat;
      const lon = rtLoc?.lon ?? driver.current_lon;
      if (lat == null || lon == null) return null;
      return { driver, lat, lon };
    })
    .filter(Boolean) as { driver: Driver; lat: number; lon: number }[];

  const center: [number, number] = driverMarkers.length > 0
    ? [
        driverMarkers.reduce((sum, m) => sum + m.lat, 0) / driverMarkers.length,
        driverMarkers.reduce((sum, m) => sum + m.lon, 0) / driverMarkers.length,
      ]
    : [41.8781, -87.6298];

  const selectedDriver = drivers.find((d) => d.id === selectedDriverId);
  const currentHistoryPoint = history[currentIndex];
  const currentTime = currentHistoryPoint?.last_updated
    ? new Date(currentHistoryPoint.last_updated).toLocaleTimeString()
    : null;

  const driverSelectData = drivers.map((d) => ({
    value: d.id,
    label: `${d.name} (${d.is_online ? "Online" : "Offline"})`,
  }));

  return (
    <Container size="xl" py="xl" style={{ height: "calc(100vh - 120px)" }}>
      <Stack gap="md" h="100%">
        <Title order={2}>GPS Tracking</Title>

        <Grid gutter="md" style={{ flex: 1 }}>
          <Grid.Col span={3}>
            <Stack gap="md">
              <Select
                label="Select Driver"
                placeholder="Choose a driver..."
                data={driverSelectData}
                value={selectedDriverId}
                onChange={setSelectedDriverId}
                searchable
                clearable
              />

              {selectedDriver && (
                <Paper p="sm" radius="md" withBorder>
                  <Stack gap="xs">
                    <Text fw={600}>{selectedDriver.name}</Text>
                    <Group gap="xs">
                      <Badge color={selectedDriver.is_online ? "green" : "gray"} size="sm">
                        {selectedDriver.is_online ? "Online" : "Offline"}
                      </Badge>
                      <Badge variant="outline" size="sm">{selectedDriver.status}</Badge>
                    </Group>
                    <Text size="xs" c="dimmed">
                      Packages: {selectedDriver.package_count}
                    </Text>
                    <Text size="xs" c="dimmed">
                      History points: {historyPositions.length}
                    </Text>
                  </Stack>
                </Paper>
              )}

              {selectedDriverId && (
                <RoutePlaybackControls
                  isPlaying={isPlaying}
                  onTogglePlay={handleTogglePlay}
                  onStop={handleStop}
                  currentIndex={currentIndex}
                  totalPoints={historyPositions.length}
                  onSeek={handleSeek}
                  speed={speed}
                  onSpeedChange={setSpeed}
                  currentTime={currentTime}
                />
              )}
            </Stack>
          </Grid.Col>

          <Grid.Col span={9}>
            <Paper radius="md" withBorder style={{ height: "100%", minHeight: 500, overflow: "hidden" }}>
              <MapContainer
                center={center}
                zoom={12}
                style={{ height: "100%", width: "100%" }}
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />

                {driverMarkers.map(({ driver, lat, lon }) => (
                  <DriverMarker
                    key={driver.id}
                    driver={driver}
                    lat={lat}
                    lon={lon}
                    isSelected={selectedDriverId === driver.id}
                    onClick={() => setSelectedDriverId(driver.id)}
                  />
                ))}

                {selectedDriverId && historyPositions.length >= 2 && (
                  <RoutePlayback
                    positions={historyPositions}
                    currentIndex={currentIndex}
                  />
                )}
              </MapContainer>
            </Paper>
          </Grid.Col>
        </Grid>
      </Stack>
    </Container>
  );
}
