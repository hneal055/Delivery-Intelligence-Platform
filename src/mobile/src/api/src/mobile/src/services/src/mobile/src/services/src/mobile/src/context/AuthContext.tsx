import React, { createContext, useContext, useState, useEffect } from "react";
import {
  initializeTokenCache,
  registerUnauthorizedHandler,
  setTokens,
  clearTokens,
} from "../services/tokenProvider";

interface AuthContextType {
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, refreshToken?: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const bootstrapAsync = async () => {
      try {
        const savedToken = await initializeTokenCache();
        setToken(savedToken);
      } catch (e) {
        console.error("[AuthProvider] Failed to restore token:", e);
      } finally {
        setIsLoading(false);
      }
    };

    registerUnauthorizedHandler(() => {
      setToken(null);
    });

    bootstrapAsync();
  }, []);

  const login = async (newToken: string, refreshToken?: string) => {
    await setTokens(newToken, refreshToken);
    setToken(newToken);
  };

  const logout = async () => {
    await clearTokens();
    setToken(null);
  };

  return (
    <AuthContext.Provider
      value={{
        token,
        isAuthenticated: !!token,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
