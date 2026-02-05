import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, act, waitFor } from "@testing-library/react";
import { SettingsProvider, useSettings } from "../../contexts/SettingsContext";
import { DEFAULT_SETTINGS } from "../../types/settings";

// Test component to access context values
function TestConsumer() {
  const { settings, updateCategory, resetSettings, isLoading } = useSettings();
  return (
    <div>
      <span data-testid="isLoading">{String(isLoading)}</span>
      <span data-testid="scrollSpeed">{settings.graphView.scrollSpeed}</span>
      <span data-testid="fontSize">{settings.appearance.fontSize}</span>
      <span data-testid="editor">{settings.editor.preferredEditor}</span>
      <button
        data-testid="updateScrollSpeed"
        onClick={() => updateCategory("graphView", { scrollSpeed: 0.5 })}
      >
        Update Scroll Speed
      </button>
      <button data-testid="resetSettings" onClick={() => resetSettings()}>
        Reset
      </button>
    </div>
  );
}

describe("SettingsContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset localStorage mock
    (window.localStorage.getItem as ReturnType<typeof vi.fn>).mockReturnValue(null);
  });

  it("renders children without crashing", async () => {
    render(
      <SettingsProvider>
        <div data-testid="child">Hello</div>
      </SettingsProvider>
    );

    expect(screen.getByTestId("child")).toBeInTheDocument();
  });

  it("provides default settings when localStorage is empty", async () => {
    render(
      <SettingsProvider>
        <TestConsumer />
      </SettingsProvider>
    );

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.getByTestId("isLoading")).toHaveTextContent("false");
    });

    expect(screen.getByTestId("scrollSpeed")).toHaveTextContent(
      String(DEFAULT_SETTINGS.graphView.scrollSpeed)
    );
    expect(screen.getByTestId("fontSize")).toHaveTextContent(
      DEFAULT_SETTINGS.appearance.fontSize
    );
    expect(screen.getByTestId("editor")).toHaveTextContent(
      DEFAULT_SETTINGS.editor.preferredEditor
    );
  });

  it("updateCategory updates specific category", async () => {
    render(
      <SettingsProvider>
        <TestConsumer />
      </SettingsProvider>
    );

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.getByTestId("isLoading")).toHaveTextContent("false");
    });

    // Initial value
    expect(screen.getByTestId("scrollSpeed")).toHaveTextContent(
      String(DEFAULT_SETTINGS.graphView.scrollSpeed)
    );

    // Update the setting
    await act(async () => {
      screen.getByTestId("updateScrollSpeed").click();
    });

    // Verify updated value
    expect(screen.getByTestId("scrollSpeed")).toHaveTextContent("0.5");

    // Verify localStorage was called to save
    expect(window.localStorage.setItem).toHaveBeenCalled();
  });

  it("resetSettings returns to defaults", async () => {
    render(
      <SettingsProvider>
        <TestConsumer />
      </SettingsProvider>
    );

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.getByTestId("isLoading")).toHaveTextContent("false");
    });

    // Update a setting first
    await act(async () => {
      screen.getByTestId("updateScrollSpeed").click();
    });

    expect(screen.getByTestId("scrollSpeed")).toHaveTextContent("0.5");

    // Reset settings
    await act(async () => {
      screen.getByTestId("resetSettings").click();
    });

    // Should be back to default
    await waitFor(() => {
      expect(screen.getByTestId("scrollSpeed")).toHaveTextContent(
        String(DEFAULT_SETTINGS.graphView.scrollSpeed)
      );
    });
  });

  it("loads from localStorage on init", async () => {
    const savedSettings = {
      graphView: { ...DEFAULT_SETTINGS.graphView, scrollSpeed: 0.8 },
      appearance: DEFAULT_SETTINGS.appearance,
      editor: DEFAULT_SETTINGS.editor,
      general: DEFAULT_SETTINGS.general,
    };

    (window.localStorage.getItem as ReturnType<typeof vi.fn>).mockReturnValue(
      JSON.stringify(savedSettings)
    );

    render(
      <SettingsProvider>
        <TestConsumer />
      </SettingsProvider>
    );

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.getByTestId("isLoading")).toHaveTextContent("false");
    });

    // Should have the saved value from localStorage
    expect(screen.getByTestId("scrollSpeed")).toHaveTextContent("0.8");
  });

  it("throws error when useSettings is used outside provider", () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    expect(() => {
      render(<TestConsumer />);
    }).toThrow("useSettings must be used within a SettingsProvider");

    consoleSpy.mockRestore();
  });
});
