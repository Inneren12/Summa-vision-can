import { render, screen } from "@testing-library/react";
import RootLayout from "@/app/layout";

// next/jest already provides a Proxy mock for next/font/* via nextFontMock.js.
// No custom jest.mock needed — the built-in mock handles any font constructor.

describe("RootLayout", () => {
  it("renders children", () => {
    render(
      <RootLayout>
        <div data-testid="child">Hello</div>
      </RootLayout>
    );
    expect(screen.getByTestId("child")).toBeInTheDocument();
  });

  it("sets lang attribute on html element", () => {
    render(
      <RootLayout>
        <span>test</span>
      </RootLayout>
    );
    expect(document.documentElement.lang).toBe("en");
  });
});
