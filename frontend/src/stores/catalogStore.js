import { create } from "zustand";

export const useCatalogStore = create((set) => ({
  current: null,
  setCurrent: (catalog) => set({ current: catalog }),
  clear: () => set({ current: null }),
}));
