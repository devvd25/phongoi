import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, getToken } from "./api";
import type { User } from "./types";

interface AuthCtx {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (data: { full_name: string; email: string; password: string; role: string; school_id?: number | null }) => Promise<User>;
  logout: () => void;
  /** Lưu phiên từ phản hồi {token, user}, ví dụ sau khi đặt lại mật khẩu. */
  session: (res: { token: string; user: User }) => User;
  setUser: (u: User) => void;
}

const Ctx = createContext<AuthCtx>(null!);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) return setReady(true);
    api<User>("/auth/me")
      .then(setUser)
      .catch(() => localStorage.removeItem("token"))
      .finally(() => setReady(true));
  }, []);

  const save = useCallback((res: { token: string; user: User }) => {
    localStorage.setItem("token", res.token);
    setUser(res.user);
    return res.user;
  }, []);
  const login = useCallback(async (email: string, password: string) => save(await api("/auth/login", { body: { email, password } })), [save]);
  const register = useCallback(async (data: Parameters<AuthCtx["register"]>[0]) => save(await api("/auth/register", { body: data })), [save]);
  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setUser(null);
  }, []);

  return <Ctx.Provider value={{ user, ready, login, register, logout, setUser, session: save }}>{children}</Ctx.Provider>;
}

export const useAuth = () => useContext(Ctx);

export function homeFor(u: User | null): string {
  if (u?.role === "landlord") return "/chu-tro";
  if (u?.role === "admin") return "/admin";
  return "/";
}
