"use client"
import * as React from "react"
import { useRouter, usePathname } from "next/navigation"
import { authApi, User, setToken, removeToken, getToken } from "./api-client"

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (data: FormData) => Promise<void>;
  register: (data: any) => Promise<void>;
  logout: () => void;
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = React.useState<User | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);
  const router = useRouter();
  const pathname = usePathname();

  React.useEffect(() => {
    const initAuth = async () => {
      const token = getToken();
      if (token) {
        try {
          const userData = await authApi.me();
          setUser(userData);
        } catch (error) {
          removeToken();
        }
      }
      setIsLoading(false);
    };
    initAuth();
  }, []);

  // Simple route guard for demo purposes
  React.useEffect(() => {
    if (!isLoading && !user && !pathname.startsWith('/login') && !pathname.startsWith('/signup')) {
      router.push('/login');
    }
  }, [isLoading, user, pathname, router]);

  const login = async (data: FormData) => {
    const token = await authApi.login(data);
    setToken(token.access_token);
    const userData = await authApi.me();
    setUser(userData);
    router.push('/dashboard');
  };

  const register = async (data: any) => {
    await authApi.register(data);
    // After successful registration, usually redirect to login or auto-login.
    // For now we just push to login.
    router.push('/login');
  };

  const logout = () => {
    removeToken();
    setUser(null);
    router.push('/login');
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = React.useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
