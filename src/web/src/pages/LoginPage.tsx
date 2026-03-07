import { useForm } from "@mantine/form";
import {
  TextInput,
  PasswordInput,
  Button,
  Paper,
  Title,
  Stack,
  Text,
  Center,
  Box,
  Group,
  Alert,
  Divider,
  Badge,
  UnstyledButton,
  SimpleGrid,
  Tooltip,
} from "@mantine/core";
import {
  IconTruck,
  IconUser,
  IconLock,
  IconAlertCircle,
  IconKey,
} from "@tabler/icons-react";
import { Navigate } from "react-router-dom";
import { useLogin } from "../hooks/useAuth";
import { useAuthStore } from "../stores/authStore";

interface DemoCredential {
  label: string;
  username: string;
  password: string;
  color: string;
}

const DEMO_CREDENTIALS: DemoCredential[] = [
  { label: "Admin",      username: "admin",       password: "adminpassword",      color: "red"   },
  { label: "Dispatcher", username: "dispatcher1", password: "dispatcherpassword", color: "blue"  },
  { label: "Driver",     username: "driver1",     password: "driverpassword",     color: "green" },
];

export function LoginPage() {
  const token = useAuthStore((s) => s.token);
  const loginMutation = useLogin();

  const form = useForm({
    initialValues: { username: "", password: "" },
    validate: {
      username: (v) => (v.trim().length < 1 ? "Username is required" : null),
      password: (v) => (v.length < 1 ? "Password is required" : null),
    },
  });

  if (token) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = form.onSubmit(({ username, password }) => {
    loginMutation.mutate({ username, password });
  });

  const fillCredential = (cred: DemoCredential) => {
    form.setValues({ username: cred.username, password: cred.password });
    loginMutation.reset();
  };

  return (
    <Center h="100vh" bg="gray.1">
      <Paper shadow="xl" radius="lg" w={440} style={{ overflow: "hidden" }}>

        {/* Branded header */}
        <Box
          p="xl"
          style={{ background: "linear-gradient(135deg, #1971c2 0%, #1098ad 100%)" }}
        >
          <Group justify="center" mb={8}>
            <IconTruck size={40} color="white" />
          </Group>
          <Title order={2} ta="center" c="white" fw={700}>
            Delivery Intelligence
          </Title>
          <Text ta="center" c="rgba(255,255,255,0.75)" size="sm" mt={4}>
            Dispatcher Console
          </Text>
        </Box>

        {/* Login form */}
        <Box p="xl">
          <form onSubmit={handleSubmit} noValidate>
            <Stack gap="md">
              <TextInput
                label="Username"
                placeholder="Enter your username"
                leftSection={<IconUser size={16} />}
                autoComplete="username"
                {...form.getInputProps("username")}
              />

              <PasswordInput
                label="Password"
                placeholder="Enter your password"
                leftSection={<IconLock size={16} />}
                autoComplete="current-password"
                {...form.getInputProps("password")}
              />

              {loginMutation.isError && (
                <Alert
                  icon={<IconAlertCircle size={16} />}
                  color="red"
                  variant="light"
                  title="Login failed"
                >
                  Invalid username or password. Please try again.
                </Alert>
              )}

              <Button
                type="submit"
                fullWidth
                size="md"
                loading={loginMutation.isPending}
                loaderProps={{ type: "dots" }}
                style={{ background: "linear-gradient(135deg, #1971c2 0%, #1098ad 100%)" }}
              >
                Sign In
              </Button>

              {/* Demo credential quick-fill */}
              <Divider
                label={
                  <Group gap={4}>
                    <IconKey size={12} />
                    <Text size="xs" c="dimmed">Demo credentials</Text>
                  </Group>
                }
                labelPosition="center"
              />

              <SimpleGrid cols={3} spacing="xs">
                {DEMO_CREDENTIALS.map((cred) => (
                  <Tooltip
                    key={cred.username}
                    label={`${cred.username} / ${cred.password}`}
                    withArrow
                    position="bottom"
                    fz="xs"
                  >
                    <UnstyledButton
                      onClick={() => fillCredential(cred)}
                      style={{ textAlign: "center" }}
                    >
                      <Badge
                        color={cred.color}
                        variant="light"
                        fullWidth
                        size="lg"
                        style={{ cursor: "pointer" }}
                      >
                        {cred.label}
                      </Badge>
                    </UnstyledButton>
                  </Tooltip>
                ))}
              </SimpleGrid>

              <Text size="xs" c="dimmed" ta="center">
                Click a role badge to auto-fill credentials
              </Text>
            </Stack>
          </form>
        </Box>
      </Paper>
    </Center>
  );
}
