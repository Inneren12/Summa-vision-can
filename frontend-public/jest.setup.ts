import "@testing-library/jest-dom";

// Mock next/font/google — the module relies on Next.js build-time transforms
// that are unavailable in the Jest/JSDOM environment.
jest.mock("next/font/google", () => {
  const fontMock = () => ({
    className: "mocked-font",
    variable: "--mocked-font",
    style: { fontFamily: "mocked" },
  });
  return new Proxy(
    {},
    {
      get: (_target, prop) => {
        if (typeof prop === "string" && prop !== "__esModule") return fontMock;
        return undefined;
      },
    },
  );
});
