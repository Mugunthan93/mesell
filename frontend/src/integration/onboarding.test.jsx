/**
 * Integration test: drives the real Onboarding component through its full flow,
 * with the API mocked at the network layer by msw. This exercises:
 *   - React state machine across the two steps
 *   - The axios client + JWT interceptor + authStore login
 *   - The msw backend (stand-in for the real FastAPI)
 */
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import Onboarding from "../pages/Onboarding.jsx";
import { server } from "../test/server.js";
import { useAuthStore } from "../stores/authStore.js";

function renderOnboardingWithRouter() {
  return render(
    <MemoryRouter initialEntries={["/onboarding"]}>
      <Routes>
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/dashboard" element={<div>Dashboard landed</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

afterEach(() => {
  useAuthStore.getState().logout();
  server.resetHandlers();
});

describe("Onboarding flow integration", () => {
  it("renders step 1 (phone input) by default", () => {
    renderOnboardingWithRouter();
    expect(screen.getByText("Sign in to MeeSell")).toBeInTheDocument();
    expect(screen.getByText(/Send OTP/)).toBeInTheDocument();
  });

  it("completes happy-path login and lands on dashboard", async () => {
    renderOnboardingWithRouter();

    const phone = screen.getByPlaceholderText("+91XXXXXXXXXX");
    await userEvent.clear(phone);
    await userEvent.type(phone, "+919876543210");
    await userEvent.click(screen.getByRole("button", { name: /Send OTP/i }));

    // Step 2 — OTP input
    const otp = await screen.findByPlaceholderText("OTP");
    await userEvent.type(otp, "1234");
    await userEvent.click(screen.getByRole("button", { name: /Verify/i }));

    await waitFor(() =>
      expect(screen.getByText("Dashboard landed")).toBeInTheDocument(),
    );
    // Token stored in authStore.
    expect(useAuthStore.getState().token).toBe("fake-jwt-token");
    expect(useAuthStore.getState().user.phone).toBe("+919876543210");
  });

  it("shows backend error when send-otp fails", async () => {
    server.use(
      http.post("*/api/v1/auth/send-otp", () =>
        new HttpResponse(JSON.stringify({ detail: "phone must be in +91XXXXXXXXXX format" }), {
          status: 422,
        }),
      ),
    );
    renderOnboardingWithRouter();
    await userEvent.click(screen.getByRole("button", { name: /Send OTP/i }));
    expect(await screen.findByText(/phone must be in/)).toBeInTheDocument();
  });

  it("shows error on wrong OTP", async () => {
    renderOnboardingWithRouter();
    await userEvent.type(screen.getByPlaceholderText("+91XXXXXXXXXX"), "+919876543210");
    await userEvent.click(screen.getByRole("button", { name: /Send OTP/i }));

    server.use(
      http.post("*/api/v1/auth/verify-otp", () =>
        new HttpResponse(JSON.stringify({ detail: "Invalid or expired OTP" }), { status: 401 }),
      ),
    );

    const otp = await screen.findByPlaceholderText("OTP");
    await userEvent.type(otp, "0000");
    await userEvent.click(screen.getByRole("button", { name: /Verify/i }));

    expect(await screen.findByText(/Invalid or expired OTP/)).toBeInTheDocument();
    expect(useAuthStore.getState().token).toBeNull();
  });

  it("change-number resets to step 1", async () => {
    renderOnboardingWithRouter();
    await userEvent.type(screen.getByPlaceholderText("+91XXXXXXXXXX"), "+919876543210");
    await userEvent.click(screen.getByRole("button", { name: /Send OTP/i }));
    await screen.findByPlaceholderText("OTP");
    await userEvent.click(screen.getByText(/Change number/));
    // Back to step 1.
    expect(screen.getByText(/Send OTP/)).toBeInTheDocument();
  });
});
