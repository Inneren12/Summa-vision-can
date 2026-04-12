// Manual Jest mock for next/font/google.
// next/font relies on Next.js compiler transforms unavailable in Jest.
function createFontMock() {
  return function () {
    return {
      className: 'mock-font',
      variable: '--mock-font-var',
      style: { fontFamily: 'mock-font-family' },
    };
  };
}

module.exports = {
  Bricolage_Grotesque: createFontMock(),
  DM_Sans: createFontMock(),
  JetBrains_Mono: createFontMock(),
  // Legacy fonts (kept for any remaining test that imports them)
  Geist: createFontMock(),
  Geist_Mono: createFontMock(),
};
