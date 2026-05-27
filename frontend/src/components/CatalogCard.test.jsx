import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import CatalogCard from "./CatalogCard.jsx";

function withRouter(node) {
  return <MemoryRouter>{node}</MemoryRouter>;
}

describe("CatalogCard", () => {
  it("renders name, status, and category", () => {
    render(
      withRouter(
        <CatalogCard
          catalog={{
            id: "c-1",
            name: "Diwali Sale",
            status: "draft",
            category: "Kurtis",
            created_at: "2026-05-27T07:00:00Z",
          }}
        />,
      ),
    );
    expect(screen.getByText("Diwali Sale")).toBeInTheDocument();
    expect(screen.getByText("draft")).toBeInTheDocument();
    expect(screen.getByText(/Kurtis/)).toBeInTheDocument();
  });

  it("renders score row when quality_score is set", () => {
    render(
      withRouter(
        <CatalogCard
          catalog={{
            id: "c-2",
            name: "Sarees",
            status: "validated",
            category: "Sarees",
            created_at: "2026-05-27T07:00:00Z",
            quality_score: 92,
          }}
        />,
      ),
    );
    expect(screen.getByText(/Score 92/)).toBeInTheDocument();
  });

  it("omits score row when quality_score is null", () => {
    render(
      withRouter(
        <CatalogCard
          catalog={{
            id: "c-3",
            name: "Tops",
            status: "draft",
            category: null,
            created_at: "2026-05-27T07:00:00Z",
            quality_score: null,
          }}
        />,
      ),
    );
    expect(screen.queryByText(/Score/)).toBeNull();
  });

  it("links to the catalog detail page", () => {
    render(
      withRouter(
        <CatalogCard
          catalog={{
            id: "c-4",
            name: "Jeans",
            status: "draft",
            category: "Jeans",
            created_at: "2026-05-27T07:00:00Z",
          }}
        />,
      ),
    );
    const link = screen.getByRole("link");
    expect(link.getAttribute("href")).toBe("/catalog/c-4");
  });
});
