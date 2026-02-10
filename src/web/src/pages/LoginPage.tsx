import { useState } from "react";
import { TextInput, PasswordInput, Button, Paper, Title, Stack, Text, Center } from "@mantine/core";
import { Navigate } from "react-router-dom";
import { useLogin } from "../hooks/useAuth";
import { useAuthStore } from "../stores/authStore";

export function LoginPage() {
  const token = useAuthStore((s) => s.token);
  const loginMutation = useLogin();
  const [username, setUsername] = useState("dispatcher1");
  const [password, setPassword] = useState("dispatcherpassword");

  if (token) {
    return <Navigate to="/" replace />;
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loginMutation.mutate({ username, password });
  };

  return (
    <Center h="100vh" bg="gray.1">
      <Paper shadow="md" p="xl" radius="md" w={400}>
        <Title order={2} ta="center" mb="md">
          Delivery Intelligence
        </Title>
        <Text size="sm" c="dimmed" ta="center" mb="lg">
          Dispatcher Console
        </Text>

        <form onSubmit={handleSubmit}>
          <Stack>
            <TextInput
              label="Username"
              value={username}
              onChange={(e) => setUsername(e.currentTarget.value)}
              required
            />
            <PasswordInput
              label="Password"
              value={password}
              onChange={(e) => setPassword(e.currentTarget.value)}
              required
            />
            {loginMutation.isError && (
              <Text size="sm" c="red">
                Login failed. Check your credentials.
              </Text>
            )}
            <Button type="submit" fullWidth loading={loginMutation.isPending}>
              Sign In
            </Button>
          </Stack>
        </form>
      </Paper>
    </Center>
  );
}
