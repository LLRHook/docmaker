import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
  length: 0,
  key: vi.fn(),
};
Object.defineProperty(window, "localStorage", { value: localStorageMock });

// Mock pyloid-js
vi.mock("pyloid-js", () => ({
  ipc: {
    DocmakerAPI: {
      get_settings: vi.fn().mockResolvedValue("{}"),
      save_settings_ipc: vi.fn().mockResolvedValue('{"success":true}'),
      reset_settings_ipc: vi.fn().mockResolvedValue("{}"),
      parse_only: vi.fn().mockResolvedValue('{"graph":{"nodes":[],"edges":[]},"stats":{"filesParsed":0,"classesFound":0,"endpointsFound":0}}'),
      select_folder: vi.fn().mockResolvedValue(null),
      open_file: vi.fn().mockResolvedValue("{}"),
      resize_window: vi.fn().mockResolvedValue('{"success":true}'),
      get_window_size: vi.fn().mockResolvedValue('{"width":1280,"height":720}'),
    },
  },
  pyloidReadyManager: {
    isReady: vi.fn().mockReturnValue(false),
    whenReady: vi.fn().mockRejectedValue(new Error("Not in Pyloid environment")),
  },
}));
