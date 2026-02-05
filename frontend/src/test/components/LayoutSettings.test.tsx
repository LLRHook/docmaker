import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { LayoutSettings } from "../../components/settings/LayoutSettings";
import { SettingsProvider } from "../../contexts/SettingsContext";

// Wrapper component for tests
function TestWrapper({ children }: { children: React.ReactNode }) {
  return <SettingsProvider>{children}</SettingsProvider>;
}

describe("LayoutSettings", () => {
  it("renders the Layout heading", () => {
    render(
      <TestWrapper>
        <LayoutSettings />
      </TestWrapper>
    );

    expect(screen.getByText("Layout")).toBeInTheDocument();
  });

  it("renders all window size presets", () => {
    render(
      <TestWrapper>
        <LayoutSettings />
      </TestWrapper>
    );

    expect(screen.getByText("1280×720 (HD)")).toBeInTheDocument();
    expect(screen.getByText("1366×768")).toBeInTheDocument();
    expect(screen.getByText("1920×1080 (Full HD)")).toBeInTheDocument();
    expect(screen.getByText("2560×1440 (QHD)")).toBeInTheDocument();
  });

  it("renders custom window size inputs", () => {
    render(
      <TestWrapper>
        <LayoutSettings />
      </TestWrapper>
    );

    expect(screen.getByText("Custom Window Size")).toBeInTheDocument();
    expect(screen.getByText("Width")).toBeInTheDocument();
    expect(screen.getByText("Height")).toBeInTheDocument();
  });

  it("renders sidebar width slider", () => {
    render(
      <TestWrapper>
        <LayoutSettings />
      </TestWrapper>
    );

    expect(screen.getByText("Left Sidebar Width")).toBeInTheDocument();
  });

  it("renders details panel width slider", () => {
    render(
      <TestWrapper>
        <LayoutSettings />
      </TestWrapper>
    );

    expect(screen.getByText("Right Details Panel Width")).toBeInTheDocument();
  });

  it("renders drag resize info", () => {
    render(
      <TestWrapper>
        <LayoutSettings />
      </TestWrapper>
    );

    expect(
      screen.getByText(/You can also drag the edges of the sidebars/)
    ).toBeInTheDocument();
  });

  it("shows dev mode warning when Pyloid is not available", () => {
    render(
      <TestWrapper>
        <LayoutSettings />
      </TestWrapper>
    );

    expect(
      screen.getByText("Window resizing is only available in the desktop app")
    ).toBeInTheDocument();
  });
});
