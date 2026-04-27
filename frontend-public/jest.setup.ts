import "@testing-library/jest-dom";


// jsdom (current pinned version) does not expose `structuredClone` on the
// jsdom globalThis even though Node has provided it natively since v17.
// Production code (editor/export/zipExport.ts — Phase 2.1 PR#3) relies on
// it for the click-time doc snapshot. Bind from the Node global so tests
// running under the jsdom environment behave like the browser.
if (typeof globalThis.structuredClone !== 'function') {
  globalThis.structuredClone = (value: unknown) => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const v8 = require('node:v8');
    return v8.deserialize(v8.serialize(value));
  };
}

// jsdom's Blob omits `arrayBuffer()` (still implements size/type/slice).
// Phase 2.1 PR#3 (editor/export/zipExport.ts) reads each per-preset PNG
// blob's bytes via `blob.arrayBuffer()` to feed `fflate.zipSync`. Polyfill
// here so unit + integration tests can exercise the real ZIP-packing path
// without bespoke mocks.
if (typeof (Blob.prototype as unknown as { arrayBuffer?: unknown }).arrayBuffer !== 'function') {
  Object.defineProperty(Blob.prototype, 'arrayBuffer', {
    configurable: true,
    writable: true,
    value: function arrayBuffer(this: Blob): Promise<ArrayBuffer> {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const result = reader.result;
          if (result instanceof ArrayBuffer) resolve(result);
          else reject(new Error('FileReader did not return ArrayBuffer'));
        };
        reader.onerror = () => reject(reader.error ?? new Error('FileReader error'));
        reader.readAsArrayBuffer(this);
      });
    },
  });
}

// Global mock for next/navigation router.
jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
    refresh: jest.fn(),
    back: jest.fn(),
    forward: jest.fn(),
    prefetch: jest.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
}));
