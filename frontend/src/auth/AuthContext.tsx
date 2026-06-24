import { createContext, useContext, useState, type ReactNode } from "react";
import * as api from "../api/endpoints";
import type { UserResponse } from "../api/types";

interface AuthState {
  user: UserResponse | null;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  // Token is held in memory inside the api client (S-01); user mirrors it in React state.
  const [user, setUser] = useState<UserResponse | null>(null);

  const login = async (email: string, password: string) => {
    try {
      setUser(await api.login(email, password));
    } catch (err) {
      // AUTH-001: a failed (re-)login must not leave a prior user session in state; the
      // token is already cleared in api.login, so clear the mirrored user too.
      setUser(null);
      throw err;
    }
  };

  const signup = async (email: string, password: string) => {
    await api.signup(email, password);
    await login(email, password);
  };

  const logout = () => {
    api.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, signup, logout }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
