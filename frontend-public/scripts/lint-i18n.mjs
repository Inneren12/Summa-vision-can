#!/usr/bin/env node
// Cross-platform wrapper for ESLint i18n check.
// Invokes ESLint programmatically so glob patterns and rule overrides
// don't depend on shell quoting rules (PowerShell vs bash differ).

import { ESLint } from 'eslint';

const patterns = [
  'src/app/admin/**/*.{ts,tsx}',
  'src/components/editor/**/*.{ts,tsx}',
  'src/components/admin/**/*.{ts,tsx}',
];

const eslint = new ESLint({
  overrideConfig: {
    rules: {
      'i18next/no-literal-string': 'error',
    },
  },
});

const results = await eslint.lintFiles(patterns);
const formatter = await eslint.loadFormatter('stylish');
const output = formatter.format(results);

if (output) {
  console.log(output);
}

const errorCount = results.reduce((sum, r) => sum + r.errorCount, 0);
process.exit(errorCount > 0 ? 1 : 0);
