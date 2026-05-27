import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";
import Navbar from "./Navbar.jsx";
import { useAuthStore } from "../stores/authStore.js";

afterEach(() => useAuthStore.getState().logout());

describe("Navbar", () => {
  it("shows public CTAs when logged out", () => {
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Pricing calculator/)).toBeInTheDocument();
    expect(screen.getByText(/Start free/)).toBeInTheDocument();
    expect(screen.queryByText(/Log out/)).toBeNull();
  });

  it("shows plan badge + logout when authenticated", () => {
    useAuthStore.getState().login({
      token: "t",
      user: { id: "u-1", phone: "+919876543210", plan: "pro" },
    });
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    expect(screen.getByText("PRO")).toBeInTheDocument();
    expect(screen.getByText(/Log out/)).toBeInTheDocument();
    expect(screen.queryByText(/Start free/)).toBeNull();
  });

  it("falls back to FREE when user.plan is missing", () => {
    useAuthStore.getState().login({ token: "t", user: { id: "u-1" } });
    render(
      <MemoryRouter>
        <Navbar />
      </MemoryRouter>,
    );
    expect(screen.getByText("FREE")).toBeInTheDocument();
  });
});
