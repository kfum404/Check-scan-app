// Сессия пользователя: JWT в SecureStore, bootstrap при старте, тема из профиля.
import * as SecureStore from "expo-secure-store";
import React, {
  createContext, useCallback, useContext, useEffect, useMemo, useState,
} from "react";

import { authApi, usersApi } from "../api";
import { setAuthToken } from "../api/client";
import type { User } from "../api/types";
import { ThemeProvider } from "../theme";

const TOKEN_KEY = "checkscan_token";

interface AuthCtx {
  user: User | null;
  bootstrapping: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  logout: () => Promise<void>;
  updateUser: (patch: Partial<User>) => Promise<void>;
}

const Ctx = createContext<AuthCtx>({
  user: null,
  bootstrapping: true,
  login: async () => {},
  register: async () => {},
  logout: async () => {},
  updateUser: async () => {},
});

export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [bootstrapping, setBootstrapping] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const token = await SecureStore.getItemAsync(TOKEN_KEY);
        if (token) {
          setAuthToken(token);
          setUser(await authApi.me());
        }
      } catch {
        await SecureStore.deleteItemAsync(TOKEN_KEY);
        setAuthToken(null);
      } finally {
        setBootstrapping(false);
      }
    })();
  }, []);

  const applySession = useCallback(async (token: string, u: User) => {
    await SecureStore.setItemAsync(TOKEN_KEY, token);
    setAuthToken(token);
    setUser(u);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const r = await authApi.login(email.trim(), password);
      await applySession(r.token, r.user);
    },
    [applySession]
  );

  const register = useCallback(
    async (email: string, password: string, name?: string) => {
      const r = await authApi.register(email.trim(), password, name);
      await applySession(r.token, r.user);
    },
    [applySession]
  );

  const logout = useCallback(async () => {
    await SecureStore.deleteItemAsync(TOKEN_KEY);
    setAuthToken(null);
    setUser(null);
  }, []);

  const updateUser = useCallback(async (patch: Partial<User>) => {
    const u = await usersApi.patch(patch);
    setUser(u);
  }, []);

  const value = useMemo(
    () => ({ user, bootstrapping, login, register, logout, updateUser }),
    [user, bootstrapping, login, register, logout, updateUser]
  );

  return (
    <Ctx.Provider value={value}>
      <ThemeProvider
        darkMode={user?.theme_preference === "dark"}
        onChange={(dark) => void updateUser({ theme_preference: dark ? "dark" : "light" })}
      >
        {children}
      </ThemeProvider>
    </Ctx.Provider>
  );
}
