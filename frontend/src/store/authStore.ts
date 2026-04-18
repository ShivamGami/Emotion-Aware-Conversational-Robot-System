import { create } from 'zustand';

interface User {
  username: string;
  email?: string;
  avatar?: string;
  id?: number;
}

interface AuthState {
  token: string | null;
  user: User | null;
  setToken: (token: string) => void;
  setUser: (user: User) => void;
  logout: () => void;
}

const storedUser = (() => {
  try { return JSON.parse(localStorage.getItem('user') || 'null'); }
  catch { return null; }
})();

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('token'),
  user: storedUser,

  setToken: (token) => {
    localStorage.setItem('token', token);
    set({ token });
  },

  setUser: (user) => {
    localStorage.setItem('user', JSON.stringify(user));
    set({ user });
  },

  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    set({ token: null, user: null });
  },
}));
