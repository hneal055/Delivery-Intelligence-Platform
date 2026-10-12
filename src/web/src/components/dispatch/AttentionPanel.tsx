import { Paper, Group, Text, Badge, Button, Stack, ThemeIcon } from "@mantine/core";
import { useNavigate } from "react-router-dom";
import { useAttention, attentionAction, attentionAge } from "../../hooks/useAttention";

/** Dashboard panel: what needs action now, red first. Empty means all clear. */
export function AttentionPanel() {
  const { data: items = [], isLoading, isError } = useAttention();
  const navigate = useNavigate();

  if (isLoading) return null;

  if (isError) {
    return (
      <Paper withBorder p="sm" radius="md">
        <Text size="sm" c="dimmed">Could not check for items needing attention. Retrying…</Text>
      </Paper>
    );
  }

  if (items.length === 0) {
    return (
      <Paper withBorder p="sm" radius="md">
        <Group gap="xs">
          <ThemeIcon color="teal" size="sm" radius="xl">✓</ThemeIcon>
          <Text size="sm" fw={500}>Needs attention: all clear</Text>
        </Group>
      </Paper>
    );
  }

  const red = items.filter((i) => i.severity === "red").length;

  return (
    <Paper withBorder p="sm" radius="md" style={{ borderColor: red ? "var(--mantine-color-red-5)" : "var(--mantine-color-orange-5)" }}>
      <Group justify="space-between" mb="xs">
        <Text fw={600}>Needs attention</Text>
        <Group gap={6}>
          {red > 0 && <Badge color="red">{red} urgent</Badge>}
          {items.length - red > 0 && <Badge color="orange">{items.length - red} warning</Badge>}
        </Group>
      </Group>
      <Stack gap={6} mah={220} style={{ overflowY: "auto" }}>
        {items.map((item) => {
          const action = attentionAction(item);
          const age = attentionAge(item.since);
          return (
            <Group key={item.key} justify="space-between" wrap="nowrap" gap="sm">
              <Group gap="sm" wrap="nowrap" style={{ minWidth: 0 }}>
                <Badge color={item.severity === "red" ? "red" : "orange"} variant="filled" size="xs" circle> </Badge>
                <div style={{ minWidth: 0 }}>
                  <Text size="sm" fw={500} truncate>{item.title}</Text>
                  <Text size="xs" c="dimmed" truncate>
                    {item.detail}{age ? ` · ${age}` : ""}
                  </Text>
                </div>
              </Group>
              <Button
                size="xs"
                variant="light"
                color={item.severity === "red" ? "red" : "orange"}
                onClick={() => navigate(action.to)}
                style={{ flexShrink: 0 }}
              >
                {action.label}
              </Button>
            </Group>
          );
        })}
      </Stack>
    </Paper>
  );
}
