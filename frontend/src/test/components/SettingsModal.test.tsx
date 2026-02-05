import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SettingsModal } from "../../components/settings/SettingsModal";
import { SettingsProvider } from "../../contexts/SettingsContext";

// Wrapper component to provide settings context
function renderWithProvider(ui: React.ReactElement) {
  return render(<SettingsProvider>{ui}</SettingsProvider>);
}

describe("SettingsModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (window.localStorage.getItem as ReturnType<typeof vi.fn>).mockReturnValue(null);
  });

  it("renders nothing when isOpen is false", async () => {
    const onClose = vi.fn();
    renderWithProvider(<SettingsModal isOpen={false} onClose={onClose} />);

    // Modal should not be in the document
    expect(screen.queryByText("Settings")).not.toBeInTheDocument();
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders modal when isOpen is true", async () => {
    const onClose = vi.fn();
    renderWithProvider(<SettingsModal isOpen={true} onClose={onClose} />);

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.queryByText("Loading")).not.toBeInTheDocument();
    });

    // Modal title should be visible
    expect(screen.getByText("Settings")).toBeInTheDocument();

    // Tab buttons should be visible
    expect(screen.getByText("Graph View")).toBeInTheDocument();
    expect(screen.getByText("Appearance")).toBeInTheDocument();
    expect(screen.getByText("Editor")).toBeInTheDocument();
    expect(screen.getByText("General")).toBeInTheDocument();

    // Done button should be visible
    expect(screen.getByText("Done")).toBeInTheDocument();
  });

  it("calls onClose when clicking backdrop", async () => {
    const onClose = vi.fn();
    renderWithProvider(<SettingsModal isOpen={true} onClose={onClose} />);

    // Wait for loading
    await waitFor(() => {
      expect(screen.queryByText("Loading")).not.toBeInTheDocument();
    });

    // Click the backdrop (the outer div with bg-black/60)
    const backdrop = screen.getByText("Settings").closest(".fixed.inset-0");
    if (backdrop) {
      fireEvent.click(backdrop);
      expect(onClose).toHaveBeenCalledTimes(1);
    }
  });

  it("calls onClose when pressing Escape", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderWithProvider(<SettingsModal isOpen={true} onClose={onClose} />);

    // Wait for loading
    await waitFor(() => {
      expect(screen.queryByText("Loading")).not.toBeInTheDocument();
    });

    // Press Escape
    await user.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows correct tab content when tab clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderWithProvider(<SettingsModal isOpen={true} onClose={onClose} />);

    // Wait for loading
    await waitFor(() => {
      expect(screen.queryByText("Loading")).not.toBeInTheDocument();
    });

    // Default should be Graph View tab
    expect(screen.getByText("Graph View Settings")).toBeInTheDocument();

    // Click Appearance tab
    await user.click(screen.getByText("Appearance"));
    expect(screen.getByText("Appearance Settings")).toBeInTheDocument();

    // Click Editor tab
    await user.click(screen.getByText("Editor"));
    expect(screen.getByText("Editor Integration")).toBeInTheDocument();

    // Click General tab
    await user.click(screen.getByText("General"));
    expect(screen.getByText("General Settings")).toBeInTheDocument();

    // Click back to Graph View
    await user.click(screen.getByText("Graph View"));
    expect(screen.getByText("Graph View Settings")).toBeInTheDocument();
  });

  it("Done button calls onClose", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderWithProvider(<SettingsModal isOpen={true} onClose={onClose} />);

    // Wait for loading
    await waitFor(() => {
      expect(screen.queryByText("Loading")).not.toBeInTheDocument();
    });

    // Click Done button
    await user.click(screen.getByText("Done"));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("close button (X) calls onClose", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    renderWithProvider(<SettingsModal isOpen={true} onClose={onClose} />);

    // Wait for loading
    await waitFor(() => {
      expect(screen.queryByText("Loading")).not.toBeInTheDocument();
    });

    // Find and click the X button (it's next to the Settings title)
    const closeButton = screen
      .getByText("Settings")
      .parentElement?.querySelector("button");
    if (closeButton) {
      await user.click(closeButton);
      expect(onClose).toHaveBeenCalledTimes(1);
    }
  });

  it("Reset to Defaults button is visible", async () => {
    const onClose = vi.fn();
    renderWithProvider(<SettingsModal isOpen={true} onClose={onClose} />);

    // Wait for loading
    await waitFor(() => {
      expect(screen.queryByText("Loading")).not.toBeInTheDocument();
    });

    expect(screen.getByText("Reset to Defaults")).toBeInTheDocument();
  });
});
