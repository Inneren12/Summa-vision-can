/**
 * Revoke an object URL after the browser has finished using it for a
 * programmatic download. Using `setTimeout(..., 0)` alone can race ahead of
 * the navigation the synthetic `<a>.click()` kicks off in some browsers, so
 * we double-defer: rAF flushes paint, the trailing setTimeout lets the
 * download commit before we free the blob.
 */
export function deferRevoke(url: string): void {
  requestAnimationFrame(() => {
    setTimeout(() => URL.revokeObjectURL(url), 100);
  });
}
