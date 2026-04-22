import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";
import i18next from "eslint-plugin-i18next";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    files: [
      "src/app/admin/**/*.{ts,tsx}",
      "src/components/editor/**/*.{ts,tsx}",
      "src/components/admin/**/*.{ts,tsx}",
    ],
    plugins: { i18next },
    rules: {
      "i18next/no-literal-string": ["warn", {
        markupOnly: true,
        ignoreAttribute: ["data-testid", "className", "id", "role", "key", "type", "name", "value"],
      }],
    },
  },
]);

export default eslintConfig;
