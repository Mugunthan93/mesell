/**
 * Integration test: the public PriceCalculator page hitting the (mocked) backend.
 */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it } from "vitest";

import PriceCalculator from "../pages/PriceCalculator.jsx";
import { server } from "../test/server.js";

afterEach(() => server.resetHandlers());

describe("PriceCalculator integration", () => {
  it("submits the form and renders the P&L breakdown returned by the backend", async () => {
    render(
      <MemoryRouter>
        <PriceCalculator />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole("button", { name: /Calculate/i }));
    expect(await screen.findByText("Net profit")).toBeInTheDocument();
    expect(screen.getByText(/16\.46%/)).toBeInTheDocument();
    expect(screen.getByText(/Drop below 500g/)).toBeInTheDocument();
  });

  it("renders backend-error message on 500", async () => {
    server.use(
      http.post("*/api/v1/pricing/calculate", () =>
        new HttpResponse(JSON.stringify({ detail: "Server exploded" }), { status: 500 }),
      ),
    );
    render(
      <MemoryRouter>
        <PriceCalculator />
      </MemoryRouter>,
    );
    await userEvent.click(screen.getByRole("button", { name: /Calculate/i }));
    await waitFor(() =>
      expect(screen.getByText(/Server exploded/)).toBeInTheDocument(),
    );
  });
});
