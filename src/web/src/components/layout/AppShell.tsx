import { AppShell as MantineAppShell, NavLink, Group, Title, Button, Text, Stack, Badge } from "@mantine/core";
import { NavLink as RouterNavLink, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "../../stores/authStore";
import { useAttentionAlerts } from "../../hooks/useAttentionAlerts";

export function AppShell() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const location = useLocation();
  const attention = useAttentionAlerts();
  const urgent = attention.filter((i) => i.severity === "red").length;

  return (
    <MantineAppShell
      header={{ height: 60 }}
      navbar={{ width: 220, breakpoint: "sm" }}
      padding="md"
    >
      <MantineAppShell.Header>
        <Group h="100%" px="md" justify="space-between">
          <Title order={3}>Delivery Intelligence</Title>
          <Group>
            <Text size="sm" c="dimmed">
              {user?.username} ({user?.role})
            </Text>
            <Button variant="subtle" color="red" size="xs" onClick={logout}>
              Logout
            </Button>
          </Group>
        </Group>
      </MantineAppShell.Header>

      <MantineAppShell.Navbar p="sm">
        <Stack gap={4}>
          <NavLink
            label="Dashboard"
            component={RouterNavLink}
            to="/"
            rightSection={
              attention.length > 0 ? (
                <Badge size="sm" circle color={urgent > 0 ? "red" : "orange"}>
                  {attention.length}
                </Badge>
              ) : undefined
            }
            active={location.pathname === "/"}
          />
          <NavLink
            label="Tracking"
            component={RouterNavLink}
            to="/tracking"
            active={location.pathname === "/tracking"}
          />
          <NavLink
            label="Scheduling"
            component={RouterNavLink}
            to="/scheduling"
            active={location.pathname === "/scheduling"}
          />
          <NavLink
            label="Drivers"
            component={RouterNavLink}
            to="/drivers"
            active={location.pathname === "/drivers"}
          />
          <NavLink
            label="Packages"
            component={RouterNavLink}
            to="/packages"
            active={location.pathname === "/packages"}
          />
          <NavLink
            label="Proof Gallery"
            component={RouterNavLink}
            to="/proofs"
            active={location.pathname === "/proofs"}
          />
        </Stack>
      </MantineAppShell.Navbar>

      <MantineAppShell.Main>
        <Outlet />
      </MantineAppShell.Main>
    </MantineAppShell>
  );
}
