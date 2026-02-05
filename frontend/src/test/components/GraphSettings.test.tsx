import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GraphSettings } from "../../components/settings/GraphSettings";
import { SettingsProvider } from "../../contexts/SettingsContext";
import { DEFAULT_SETTINGS } from "../../types/settings";

// Wrapper component to provide settings context
function renderWithProvider(ui: React.ReactElement) {
  return render(<SettingsProvider>{ui}</SettingsProvider>);
}

describe("GraphSettings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (window.localStorage.getItem as ReturnType<typeof vi.fn>).mockReturnValue(null);
  });

  it("renders all controls", async () => {
    renderWithProvider(<GraphSettings />);

    // Wait for settings to load
    await waitFor(() => {
      expect(screen.getByText("Graph View Settings")).toBeInTheDocument();
    });

    // Scroll Speed control
    expect(screen.getByText("Scroll Speed")).toBeInTheDocument();

    // Zoom Sensitivity control
    expect(screen.getByText("Zoom Sensitivity")).toBeInTheDocument();

    // Default Layout dropdown (now defaults to fcose)
    expect(screen.getByText("Default Layout")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Force-directed (fCoSE - recommended)")).toBeInTheDocument();

    // Layout Quality dropdown
    expect(screen.getByText("Layout Quality")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Balanced")).toBeInTheDocument();

    // Node Sizing dropdown
    expect(screen.getByText("Node Sizing")).toBeInTheDocument();
    expect(screen.getByDisplayValue("By Connection Count")).toBeInTheDocument();

    // Large Graph Threshold slider
    expect(screen.getByText("Large Graph Threshold")).toBeInTheDocument();

    // Animation Speed dropdown
    expect(screen.getByText("Animation Speed")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Normal")).toBeInTheDocument();

    // Show Labels checkbox
    expect(screen.getByText("Show Node Labels")).toBeInTheDocument();
    expect(screen.getByLabelText("Show Node Labels")).toBeChecked();

    // Verify there are 3 sliders (scroll speed, zoom sensitivity, large graph threshold)
    const sliders = screen.getAllByRole("slider");
    expect(sliders).toHaveLength(3);

    // Verify there are 4 comboboxes (layout, layout quality, node sizing, animation)
    const comboboxes = screen.getAllByRole("combobox");
    expect(comboboxes).toHaveLength(4);
  });

  it("slider changes update scroll speed setting", async () => {
    renderWithProvider(<GraphSettings />);

    // Wait for settings to load
    await waitFor(() => {
      expect(screen.getByText("Graph View Settings")).toBeInTheDocument();
    });

    // Find the scroll speed slider (first range input)
    const sliders = screen.getAllByRole("slider");
    const scrollSpeedSlider = sliders[0];

    // Check initial value
    expect(scrollSpeedSlider).toHaveValue(String(DEFAULT_SETTINGS.graphView.scrollSpeed));

    // Change the value
    fireEvent.change(scrollSpeedSlider, { target: { value: "0.5" } });

    // Verify the display updates
    expect(screen.getByText("0.50")).toBeInTheDocument();

    // Verify localStorage was called to save
    expect(window.localStorage.setItem).toHaveBeenCalled();
  });

  it("slider changes update zoom sensitivity setting", async () => {
    renderWithProvider(<GraphSettings />);

    // Wait for settings to load
    await waitFor(() => {
      expect(screen.getByText("Graph View Settings")).toBeInTheDocument();
    });

    // Find the zoom sensitivity slider (second range input)
    const sliders = screen.getAllByRole("slider");
    const zoomSlider = sliders[1];

    // Check initial value
    expect(zoomSlider).toHaveValue(String(DEFAULT_SETTINGS.graphView.zoomSensitivity));

    // Change the value
    fireEvent.change(zoomSlider, { target: { value: "0.35" } });

    // Verify the display updates
    expect(screen.getByText("0.35")).toBeInTheDocument();
  });

  it("checkbox toggles show labels setting", async () => {
    const user = userEvent.setup();
    renderWithProvider(<GraphSettings />);

    // Wait for settings to load
    await waitFor(() => {
      expect(screen.getByText("Graph View Settings")).toBeInTheDocument();
    });

    const checkbox = screen.getByLabelText("Show Node Labels");

    // Initial state should be checked (default is true)
    expect(checkbox).toBeChecked();

    // Toggle off
    await user.click(checkbox);
    expect(checkbox).not.toBeChecked();

    // Toggle back on
    await user.click(checkbox);
    expect(checkbox).toBeChecked();
  });

  it("select dropdown updates default layout setting", async () => {
    const user = userEvent.setup();
    renderWithProvider(<GraphSettings />);

    // Wait for settings to load
    await waitFor(() => {
      expect(screen.getByText("Graph View Settings")).toBeInTheDocument();
    });

    // Find the layout dropdown (now defaults to fcose)
    const layoutSelect = screen.getByDisplayValue("Force-directed (fCoSE - recommended)");

    // Change to Circle layout
    await user.selectOptions(layoutSelect, "circle");
    expect(layoutSelect).toHaveValue("circle");

    // Change to Grid layout
    await user.selectOptions(layoutSelect, "grid");
    expect(layoutSelect).toHaveValue("grid");
  });

  it("select dropdown updates animation speed setting", async () => {
    const user = userEvent.setup();
    renderWithProvider(<GraphSettings />);

    // Wait for settings to load
    await waitFor(() => {
      expect(screen.getByText("Graph View Settings")).toBeInTheDocument();
    });

    // Find the animation speed dropdown
    const animationSelect = screen.getByDisplayValue("Normal");

    // Change to Fast
    await user.selectOptions(animationSelect, "fast");
    expect(animationSelect).toHaveValue("fast");

    // Change to None
    await user.selectOptions(animationSelect, "none");
    expect(animationSelect).toHaveValue("none");

    // Change to Slow
    await user.selectOptions(animationSelect, "slow");
    expect(animationSelect).toHaveValue("slow");
  });

  it("loads saved settings from localStorage", async () => {
    const savedSettings = {
      graphView: {
        scrollSpeed: 0.8,
        zoomSensitivity: 0.4,
        animationSpeed: "fast",
        defaultLayout: "circle",
        showLabels: false,
      },
      appearance: DEFAULT_SETTINGS.appearance,
      editor: DEFAULT_SETTINGS.editor,
      general: DEFAULT_SETTINGS.general,
    };

    (window.localStorage.getItem as ReturnType<typeof vi.fn>).mockReturnValue(
      JSON.stringify(savedSettings)
    );

    renderWithProvider(<GraphSettings />);

    // Wait for settings to load
    await waitFor(() => {
      expect(screen.getByText("Graph View Settings")).toBeInTheDocument();
    });

    // Verify saved values are displayed
    expect(screen.getByText("0.80")).toBeInTheDocument();
    expect(screen.getByText("0.40")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Circular")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Fast")).toBeInTheDocument();
    expect(screen.getByLabelText("Show Node Labels")).not.toBeChecked();
  });
});
