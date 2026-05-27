import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ImageUploader from "./ImageUploader.jsx";

// jsdom doesn't implement URL.createObjectURL by default.
beforeAll(() => {
  globalThis.URL.createObjectURL = vi.fn(() => "blob:fake");
});

describe("ImageUploader", () => {
  it("renders drop-zone hint", () => {
    render(<ImageUploader onSelect={() => {}} />);
    expect(screen.getByText(/Drop product photos/)).toBeInTheDocument();
    expect(screen.getByText(/Up to 9 images/)).toBeInTheDocument();
  });

  it("calls onSelect with chosen files (capped at max)", async () => {
    const onSelect = vi.fn();
    render(<ImageUploader onSelect={onSelect} max={2} />);
    const file1 = new File(["a"], "a.jpg", { type: "image/jpeg" });
    const file2 = new File(["b"], "b.jpg", { type: "image/jpeg" });
    const file3 = new File(["c"], "c.jpg", { type: "image/jpeg" });
    const input = document.querySelector('input[type="file"]');
    await userEvent.upload(input, [file1, file2, file3]);

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0][0]).toHaveLength(2);
    expect(onSelect.mock.calls[0][0][0].name).toBe("a.jpg");
  });

  it("displays previews after selection", async () => {
    const { container } = render(<ImageUploader onSelect={() => {}} max={3} />);
    const input = document.querySelector('input[type="file"]');
    await userEvent.upload(input, [new File(["a"], "a.jpg", { type: "image/jpeg" })]);
    // <img alt=""> has no implicit role per WAI-ARIA — query by tag.
    const previews = container.querySelectorAll("img");
    expect(previews).toHaveLength(1);
    expect(previews[0].getAttribute("src")).toBe("blob:fake");
  });
});
