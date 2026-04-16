import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import InfographicEditor from "../../src/components/editor";

class MockFileReader {
  public onload: ((ev: { target: { result: string } }) => void) | null = null;
  readAsText() {
    this.onload?.({ target: { result: "{bad json" } });
  }
}

describe("editor UI a11y + import warnings", () => {
  test("renders tab semantics + import control + in-app import error without alert()", async () => {
    const alertSpy = jest.spyOn(window, "alert").mockImplementation(() => {});
    const originalFileReader = window.FileReader;
    Object.defineProperty(window, "FileReader", {
      writable: true,
      value: MockFileReader,
    });

    const { container } = render(<InfographicEditor />);

    expect(screen.getByRole("tablist", { name: /left panel sections/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /templates tab/i })).toHaveAttribute("aria-controls");
    expect(screen.getByRole("tabpanel")).toBeInTheDocument();

    expect(screen.getByRole("tablist", { name: /editor mode/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /import document from json/i })).toBeInTheDocument();

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["bad"], "bad.json", { type: "application/json" });
    fireEvent.change(fileInput, { target: { files: [file] } });

    await waitFor(() => {
      expect(screen.getByText("Invalid JSON file")).toBeInTheDocument();
    });
    expect(alertSpy).not.toHaveBeenCalled();

    Object.defineProperty(window, "FileReader", {
      writable: true,
      value: originalFileReader,
    });
  });
});
