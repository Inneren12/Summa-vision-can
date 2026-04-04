import { render, screen } from "@testing-library/react";
import RootLayout from "@/app/layout";

// Mock next/font/google to avoid network calls in tests
jest.mock("next/font/google", () => ({
  Geist: () => ({ variable: "--font-geist-sans", className: "mock-geist" }),
  Geist_Mono: () => ({
    variable: "--font-geist-mono",
    className: "mock-geist-mono",
  }),
}));

describe("RootLayout", () => {
  it("renders children", () => {
    render(
      <RootLayout>
        <div data-testid="child">Hello</div>
      </RootLayout>
    );
    expect(screen.getByTestId("child")).toBeInTheDocument();
  });

  it("applies background class to body", () => {
    render(
      <RootLayout>
        <span>test</span>
      </RootLayout>
    );
    // RootLayout renders <html> + <body>, which React promotes to the
    // real document.body as singleton elements in jsdom.
    expect(document.body.className).toContain("bg-background");
  });
});
