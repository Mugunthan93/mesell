import { beforeEach, describe, expect, it } from "vitest";
import { useCatalogStore } from "./catalogStore.js";

beforeEach(() => useCatalogStore.getState().clear());

describe("catalogStore", () => {
  it("setCurrent stores catalog", () => {
    useCatalogStore.getState().setCurrent({ id: "c-1", name: "Test" });
    expect(useCatalogStore.getState().current.name).toBe("Test");
  });

  it("clear resets to null", () => {
    useCatalogStore.getState().setCurrent({ id: "c-1" });
    useCatalogStore.getState().clear();
    expect(useCatalogStore.getState().current).toBeNull();
  });
});
