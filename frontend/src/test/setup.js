import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./server.js";

// MSW lifecycle.
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => {
  server.resetHandlers();
  // Reset Zustand stores between tests so authStore.token / catalogStore don't leak.
  if (typeof window !== "undefined" && window.localStorage) {
    window.localStorage.clear();
  }
});
afterAll(() => server.close());
