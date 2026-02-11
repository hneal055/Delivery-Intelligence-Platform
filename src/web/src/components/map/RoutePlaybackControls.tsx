import { Paper, Group, ActionIcon, Slider, Select, Text } from "@mantine/core";
import { IconPlayerPlay, IconPlayerPause, IconPlayerStop } from "@tabler/icons-react";

interface RoutePlaybackControlsProps {
  isPlaying: boolean;
  onTogglePlay: () => void;
  onStop: () => void;
  currentIndex: number;
  totalPoints: number;
  onSeek: (index: number) => void;
  speed: string;
  onSpeedChange: (speed: string) => void;
  currentTime: string | null;
}

export function RoutePlaybackControls({
  isPlaying,
  onTogglePlay,
  onStop,
  currentIndex,
  totalPoints,
  onSeek,
  speed,
  onSpeedChange,
  currentTime,
}: RoutePlaybackControlsProps) {
  return (
    <Paper p="sm" radius="md" withBorder>
      <Group gap="sm" align="center">
        <ActionIcon
          variant="filled"
          color={isPlaying ? "orange" : "blue"}
          onClick={onTogglePlay}
          disabled={totalPoints < 2}
        >
          {isPlaying ? <IconPlayerPause size={16} /> : <IconPlayerPlay size={16} />}
        </ActionIcon>
        <ActionIcon variant="light" color="gray" onClick={onStop} disabled={totalPoints < 2}>
          <IconPlayerStop size={16} />
        </ActionIcon>

        <Slider
          value={currentIndex}
          onChange={onSeek}
          min={0}
          max={Math.max(totalPoints - 1, 0)}
          step={1}
          style={{ flex: 1, minWidth: 120 }}
          disabled={totalPoints < 2}
        />

        <Select
          value={speed}
          onChange={(v) => v && onSpeedChange(v)}
          data={[
            { value: "1", label: "1x" },
            { value: "2", label: "2x" },
            { value: "5", label: "5x" },
            { value: "10", label: "10x" },
          ]}
          w={70}
          size="xs"
        />

        {currentTime && (
          <Text size="xs" c="dimmed" w={140}>
            {currentTime}
          </Text>
        )}
      </Group>
    </Paper>
  );
}
