import { create } from "zustand";
import * as api from "./api";
import { errorMessage } from "./lib/errors";
import { resetWorkspace } from "./store";

interface AuthState {
  user: api.User | null;
  loading: boolean;
  submitting: boolean;
  error: string | null;
  restoreSession: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

async function authenticate(
  operation: () => Promise<api.User>,
  set: (state: Partial<AuthState>) => void,
): Promise<void> {
  set({ submitting: true, error: null });
  try {
    set({ user: await operation(), submitting: false });
  } catch (error) {
    set({ error: errorMessage(error), submitting: false });
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: true,
  submitting: false,
  error: null,

  restoreSession: async () => {
    try {
      set({ user: await api.fetchCurrentUser(), error: null, loading: false });
    } catch {
      set({ user: null, error: null, loading: false });
    }
  },

  login: (email, password) => authenticate(() => api.login(email, password), set),
  register: (email, password) =>
    authenticate(() => api.register(email, password), set),

  logout: async () => {
    set({ submitting: true, error: null });
    try {
      await api.logout();
      resetWorkspace();
      set({ user: null, submitting: false });
    } catch (error) {
      set({ error: errorMessage(error), submitting: false });
    }
  },
}));
