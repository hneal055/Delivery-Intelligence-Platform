import { useMutation } from "@tanstack/react-query";
import { login as loginApi, getCurrentUser } from "../api/auth";
import { useAuthStore } from "../stores/authStore";

export function useLogin() {
  const setAuth = useAuthStore((s) => s.setAuth);

  return useMutation({
    mutationFn: async ({ username, password }: { username: string; password: string }) => {
      const tokenData = await loginApi(username, password);
      return tokenData;
    },
    onSuccess: async (tokenData) => {
      // Temporarily set token so getCurrentUser works
      useAuthStore.getState().setAuth(tokenData.access_token, {
        id: "",
        username: "",
        email: null,
        role: "driver",
        is_active: true,
      });

      try {
        const user = await getCurrentUser();
        setAuth(tokenData.access_token, user);
      } catch {
        // If we can't fetch user info, still keep the token with basic info
        setAuth(tokenData.access_token, {
          id: "unknown",
          username: "unknown",
          email: null,
          role: "manager",
          is_active: true,
        });
      }
    },
  });
}
