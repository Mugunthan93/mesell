import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import QualityScorecard from "./QualityScorecard.jsx";

const report = {
  catalog_id: "c-1",
  score: 92,
  passed: true,
  summary: { passed_checks: 8, warned_checks: 1, failed_checks: 0 },
  checks: [
    { name: "image_size", status: "pass", severity: "fail", weight: 12, score: 12, detail: "All images >= 1024x1024", fix: null },
    { name: "watermark", status: "warn", severity: "warn", weight: 10, score: 0, detail: "1 image has soft corner artifacts.", fix: "Re-upload cleaner photos." },
    { name: "banned_words", status: "fail", severity: "fail", weight: 13, score: 0, detail: "1 SKU contains 'nike'.", fix: "Remove brand names." },
  ],
};

describe("QualityScorecard", () => {
  it("renders nothing when report is null", () => {
    const { container } = render(<QualityScorecard report={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the score prominently", () => {
    render(<QualityScorecard report={report} />);
    expect(screen.getByText("92")).toBeInTheDocument();
  });

  it("uses green color for high score", () => {
    render(<QualityScorecard report={report} />);
    const score = screen.getByText("92");
    expect(score.className).toMatch(/emerald/);
  });

  it("uses red color for failing score", () => {
    render(<QualityScorecard report={{ ...report, score: 40 }} />);
    const score = screen.getByText("40");
    expect(score.className).toMatch(/rose/);
  });

  it("displays headline status text", () => {
    render(<QualityScorecard report={report} />);
    expect(screen.getByText(/Catalog passed and is ready to export/)).toBeInTheDocument();
  });

  it("displays a row per check with weight info", () => {
    render(<QualityScorecard report={report} />);
    expect(screen.getByText("image size")).toBeInTheDocument();
    expect(screen.getByText("watermark")).toBeInTheDocument();
    expect(screen.getByText("banned words")).toBeInTheDocument();
    expect(screen.getByText("12/12")).toBeInTheDocument();
    expect(screen.getByText("0/10")).toBeInTheDocument();
  });

  it("shows fix hint only for non-pass rows", () => {
    render(<QualityScorecard report={report} />);
    expect(screen.getByText(/Re-upload cleaner photos/)).toBeInTheDocument();
    expect(screen.getByText(/Remove brand names/)).toBeInTheDocument();
    // Pass row should not have a fix line.
    expect(screen.queryByText(/Fix: All images/)).toBeNull();
  });
});
