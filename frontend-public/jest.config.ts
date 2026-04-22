import type { Config } from "jest";
import nextJest from "next/jest.js";

const createJestConfig = nextJest({ dir: "./" });

const config: Config = {
  coverageProvider: "v8",
  testEnvironment: "jsdom",
  setupFilesAfterEnv: ["<rootDir>/jest.setup.ts"],
  transformIgnorePatterns: [
    "/node_modules/(?!(next-intl|use-intl|@formatjs|intl-messageformat|icu-minify)/)",
  ],
  moduleNameMapper: {
    "^@/(.*)$": "<rootDir>/src/$1",
    "^next-intl/server$": "<rootDir>/src/__mocks__/next-intl/server.ts",
    "^next-intl$": "<rootDir>/src/__mocks__/next-intl/index.ts",
  },
};

export default createJestConfig(config);
