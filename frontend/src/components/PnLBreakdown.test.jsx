import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PnLBreakdown from "./PnLBreakdown.jsx";

const sample = {
  selling_price: "599.00",
  cost_price: "250.00",
  shipping_cost: "65.00",
  shipping_gst: "11.70",
  payment_processing: "11.98",
  return_provision: "149.75",
  packaging: "12.00",
  ad_spend: "0.00",
  net_profit: "98.57",
  margin_percent: "16.46",
  alerts: [
    { code: "weight_slab_warning", severity: "warn", message: "Drop weight below 500g." },
  ],
};

describe("PnLBreakdown", () => {
  it("renders nothing when result is null", () => {
    const { container } = render(<PnLBreakdown result={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders every line item", () => {
    render(<PnLBreakdown result={sample} />);
    expect(screen.getByText("Selling price")).toBeInTheDocument();
    expect(screen.getByText("Cost price")).toBeInTheDocument();
    expect(screen.getByText("Shipping")).toBeInTheDocument();
    expect(screen.getByText("Shipping GST (18%)")).toBeInTheDocument();
    expect(screen.getByText("Payment processing (2%)")).toBeInTheDocument();
    expect(screen.getByText("Return provision")).toBeInTheDocument();
    expect(screen.getByText("Net profit")).toBeInTheDocument();
  });

  it("highlights net profit in green when positive", () => {
    render(<PnLBreakdown result={sample} />);
    const cell = screen.getByText(/98\.57/);
    expect(cell.className).toMatch(/emerald/);
  });

  it("highlights net profit in rose when negative", () => {
    render(<PnLBreakdown result={{ ...sample, net_profit: "-50.00" }} />);
    // The Intl formatter places ₹ between the minus and the digits ("-₹50.00").
    const cell = screen.getByText((_, el) =>
      el?.tagName === "TD" && /50\.00/.test(el.textContent) && el.textContent.includes("-"),
    );
    expect(cell.className).toMatch(/rose/);
  });

  it("renders alerts with appropriate severity colors", () => {
    render(<PnLBreakdown result={sample} />);
    const alert = screen.getByText(/Drop weight below 500g/);
    expect(alert.className).toMatch(/amber/);
  });

  it("renders critical alert in rose", () => {
    const r = {
      ...sample,
      alerts: [{ code: "low_margin", severity: "critical", message: "Margin too low." }],
    };
    render(<PnLBreakdown result={r} />);
    const alert = screen.getByText(/Margin too low/);
    expect(alert.className).toMatch(/rose/);
  });

  it("renders margin percent row", () => {
    render(<PnLBreakdown result={sample} />);
    expect(screen.getByText("16.46%")).toBeInTheDocument();
  });
});
