import { describe, expect, it } from "vitest";
import { currency, scoreColor, shortDate } from "./formatters.js";

describe("currency", () => {
  it("formats numbers with INR symbol", () => {
    expect(currency(599)).toMatch(/₹\s*599\.00/);
  });

  it("accepts numeric strings", () => {
    expect(currency("250.50")).toMatch(/₹\s*250\.50/);
  });

  it("handles negatives", () => {
    expect(currency(-23.23)).toMatch(/-/);
  });

  it("renders em-dash for nullish", () => {
    expect(currency(null)).toBe("—");
    expect(currency(undefined)).toBe("—");
    expect(currency("")).toBe("—");
  });

  it("returns the original value when not a number", () => {
    expect(currency("xyz")).toBe("xyz");
  });

  it("respects fractionDigits override", () => {
    expect(currency(599, 0)).toMatch(/₹\s*599$/);
  });
});

describe("shortDate", () => {
  it("formats an ISO string", () => {
    expect(shortDate("2026-05-27T07:00:00Z")).toMatch(/2026/);
  });

  it("returns em-dash for nullish", () => {
    expect(shortDate(null)).toBe("—");
    expect(shortDate(undefined)).toBe("—");
  });
});

describe("scoreColor", () => {
  it("green at >=80", () => {
    expect(scoreColor(80)).toMatch(/emerald/);
    expect(scoreColor(100)).toMatch(/emerald/);
  });

  it("amber 60-79", () => {
    expect(scoreColor(70)).toMatch(/amber/);
    expect(scoreColor(60)).toMatch(/amber/);
  });

  it("rose below 60", () => {
    expect(scoreColor(0)).toMatch(/rose/);
    expect(scoreColor(59)).toMatch(/rose/);
  });
});
