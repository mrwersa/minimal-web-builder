import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "./api";

vi.mock("./api", () => ({
  fetchCurrentUser: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
}));

vi.mock("./store", () => ({ resetWorkspace: vi.fn() }));

import { useAuthStore } from "./authStore";
import { resetWorkspace } from "./store";

const user = { id: "user-1", email: "owner@example.test" };

describe("authentication state", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      loading: true,
      submitting: false,
      error: null,
    });
  });

  it("restores an existing session", async () => {
    vi.mocked(api.fetchCurrentUser).mockResolvedValue(user);

    await useAuthStore.getState().restoreSession();

    expect(useAuthStore.getState()).toMatchObject({ user, loading: false, error: null });
  });

  it("treats a missing session as signed out", async () => {
    vi.mocked(api.fetchCurrentUser).mockRejectedValue(new Error("Authentication required"));

    await useAuthStore.getState().restoreSession();

    expect(useAuthStore.getState()).toMatchObject({ user: null, loading: false, error: null });
  });

  it("signs in and exposes API errors", async () => {
    vi.mocked(api.login).mockResolvedValueOnce(user);
    await useAuthStore.getState().login(user.email, "correct horse battery");
    expect(useAuthStore.getState().user).toEqual(user);

    vi.mocked(api.login).mockRejectedValueOnce(new Error("Invalid email or password"));
    await useAuthStore.getState().login(user.email, "incorrect password");
    expect(useAuthStore.getState().error).toBe("Invalid email or password");
  });

  it("clears workspace data after logout", async () => {
    useAuthStore.setState({ user });
    vi.mocked(api.logout).mockResolvedValue();

    await useAuthStore.getState().logout();

    expect(resetWorkspace).toHaveBeenCalledOnce();
    expect(useAuthStore.getState().user).toBeNull();
  });
});
