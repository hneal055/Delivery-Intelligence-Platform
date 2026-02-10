import apiClient from "./client";
import type { Token, User } from "../types";

export async function login(username: string, password: string): Promise<Token> {
  const params = new URLSearchParams();
  params.append("username", username);
  params.append("password", password);
  params.append("grant_type", "password");

  const response = await apiClient.post<Token>("/auth/token", params.toString(), {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return response.data;
}

export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>("/auth/users/me");
  return response.data;
}
