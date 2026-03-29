import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { AuthSession, LoginCredentials, UserProfile } from "../types/domain";
import { mockLogin, mockLogout, mockGetSession } from "./mock-service";
import { isMockMode } from "./config";
import { liveSelectWorkspace } from "./live-api";

interface AuthContextValue {
  user: UserProfile | null;
  workspaceId: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
  selectWorkspace: (workspaceId: string) => Promise<void>;
  error: string | null;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Check for existing session on mount
  useEffect(() => {
    mockGetSession()
      .then((session) => {
        if (session) {
          setUser(session.user);
          setWorkspaceId(session.workspaceId);
        }
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (credentials: LoginCredentials) => {
    setIsLoading(true);
    setError(null);
    try {
      const session: AuthSession = await mockLogin(credentials);
      setUser(session.user);
      setWorkspaceId(session.workspaceId);
      await queryClient.invalidateQueries();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Login failed";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      await mockLogout();
      setUser(null);
      setWorkspaceId(null);
      await queryClient.clear();
    } finally {
      setIsLoading(false);
    }
  }, [queryClient]);

  const selectWorkspace = useCallback(async (nextWorkspaceId: string) => {
    setError(null);
    if (isMockMode()) {
      setWorkspaceId(nextWorkspaceId);
      await queryClient.invalidateQueries();
      return;
    }
    setIsLoading(true);
    try {
      const session = await liveSelectWorkspace(nextWorkspaceId);
      setUser(session.user);
      setWorkspaceId(session.workspaceId);
      await queryClient.invalidateQueries();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Workspace switch failed";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [queryClient]);

  return (
    <AuthContext.Provider
      value={{
        user,
        workspaceId,
        isAuthenticated: user !== null,
        isLoading,
        login,
        logout,
        selectWorkspace,
        error,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
