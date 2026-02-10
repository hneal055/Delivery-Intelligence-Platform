import { AppShell as MantineAppShell, NavLink, Group, Title, Button, Text, Stack } from "@mantine/core";
import { NavLink as RouterNavLink, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "../../stores/authStore";

export function AppShell() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const location = useLocation();

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
            active={location.pathname === "/"}
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
        </Stack>
      </MantineAppShell.Navbar>

      <MantineAppShell.Main>
        <Outlet />
      </MantineAppShell.Main>
    </MantineAppShell>
  );
}
