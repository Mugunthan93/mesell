import { http, HttpResponse } from "msw";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { api } from "./client.js";
import { server } from "../test/server.js";
import { useAuthStore } from "../stores/authStore.js";

beforeEach(() => {
  useAuthStore.getState().logout();
});

afterEach(() => server.resetHandlers());

describe("api client", () => {
  it("attaches Bearer token from authStore", async () => {
    useAuthStore.getState().login({ token: "abc.def", user: { id: "u-1" } });

    let received = null;
    server.use(
      http.get("*/api/v1/auth/me", ({ request }) => {
        received = request.headers.get("authorization");
        return HttpResponse.json({ ok: true });
      }),
    );

    await api.get("/auth/me");
    expect(received).toBe("Bearer abc.def");
  });

  it("omits Authorization header when no token", async () => {
    let received = "not-cleared";
    server.use(
      http.get("*/api/v1/pricing/calculate", ({ request }) => {
        received = request.headers.get("authorization");
        return HttpResponse.json({ ok: true });
      }),
    );
    await api.get("/pricing/calculate");
    expect(received).toBeNull();
  });

  it("logs out on 401 response", async () => {
    useAuthStore.getState().login({ token: "expired", user: { id: "u-1" } });
    server.use(
      http.get("*/api/v1/auth/me", () =>
        new HttpResponse(JSON.stringify({ detail: "expired" }), { status: 401 }),
      ),
    );
    await api.get("/auth/me").catch(() => null);
    expect(useAuthStore.getState().token).toBeNull();
  });
});
