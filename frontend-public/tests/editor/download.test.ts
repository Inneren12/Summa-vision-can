import { deferRevoke } from "../../src/components/editor/utils/download";

describe("deferRevoke", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.restoreAllMocks();
  });

  test("uses requestAnimationFrame when available", () => {
    const revokeMock = jest.fn();
    Object.defineProperty(URL, "revokeObjectURL", { value: revokeMock, configurable: true });
    const rafSpy = jest.spyOn(window, "requestAnimationFrame").mockImplementation((cb: FrameRequestCallback) => {
      cb(0);
      return 1;
    });

    deferRevoke("blob:test");
    jest.advanceTimersByTime(101);

    expect(rafSpy).toHaveBeenCalled();
    expect(revokeMock).toHaveBeenCalledWith("blob:test");
  });

  test("falls back safely when requestAnimationFrame is unavailable", () => {
    const revokeMock = jest.fn();
    Object.defineProperty(URL, "revokeObjectURL", { value: revokeMock, configurable: true });
    const originalRaf = window.requestAnimationFrame;
    Object.defineProperty(window, "requestAnimationFrame", { value: undefined, configurable: true });

    deferRevoke("blob:no-raf");
    jest.advanceTimersByTime(200);

    expect(revokeMock).toHaveBeenCalledWith("blob:no-raf");
    Object.defineProperty(window, "requestAnimationFrame", { value: originalRaf, configurable: true });
  });
});
