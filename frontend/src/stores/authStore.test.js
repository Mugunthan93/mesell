import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "./authStore.js";

beforeEach(() => {
  useAuthStore.getState().logout();
});

describe("authStore", () => {
  it("login stores token + user", () => {
    useAuthStore.getState().login({
      token: "abc.def.ghi",
      user: { id: "u-1", phone: "+919876543210", plan: "free" },
    });
    expect(useAuthStore.getState().token).toBe("abc.def.ghi");
    expect(useAuthStore.getState().user.phone).toBe("+919876543210");
  });

  it("isAuthenticated reflects token presence", () => {
    expect(useAuthStore.getState().isAuthenticated()).toBe(false);
    useAuthStore.getState().login({ token: "t", user: { id: "u-1" } });
    expect(useAuthStore.getState().isAuthenticated()).toBe(true);
  });

  it("logout clears both fields", () => {
    useAuthStore.getState().login({ token: "t", user: { id: "u-1" } });
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().token).toBeNull();
    expect(useAuthStore.getState().user).toBeNull();
  });

  it("setUser preserves token", () => {
    useAuthStore.getState().login({ token: "t", user: { id: "u-1" } });
    useAuthStore.getState().setUser({ id: "u-1", plan: "pro" });
    expect(useAuthStore.getState().token).toBe("t");
    expect(useAuthStore.getState().user.plan).toBe("pro");
  });
});
