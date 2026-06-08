import { create } from 'zustand';
import { api, loadTokens, saveTokens } from '../api/client';
import type { TokenResponse, UserOut } from '../api/types';

interface AuthState {
  tokens: TokenResponse | null;
  user: UserOut | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  loadMe: () => Promise<void>;
  logout: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  tokens: loadTokens(),
  user: null,
  isAuthenticated: loadTokens() !== null,

  login: async (email, password) => {
    const tokens = await api.login({ email, password });
    saveTokens(tokens);
    const user = await api.me();
    set({ tokens, user, isAuthenticated: true });
  },

  register: async (email, password, name) => {
    const tokens = await api.register({ email, password, name });
    saveTokens(tokens);
    const user = await api.me();
    set({ tokens, user, isAuthenticated: true });
  },

  loadMe: async () => {
    if (!loadTokens()) return;
    try {
      const user = await api.me();
      set({ user, isAuthenticated: true });
    } catch {
      saveTokens(null);
      set({ tokens: null, user: null, isAuthenticated: false });
    }
  },

  logout: () => {
    saveTokens(null);
    set({ tokens: null, user: null, isAuthenticated: false });
  },
}));
