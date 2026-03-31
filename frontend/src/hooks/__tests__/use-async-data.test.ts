import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useAsyncData } from "../use-async-data";

describe("useAsyncData", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts with loading state", () => {
    const fetcher = vi.fn(() => new Promise<string>(() => {})); // never resolves
    const { result } = renderHook(() => useAsyncData(fetcher));

    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it("returns data on successful fetch", async () => {
    const fetcher = vi.fn().mockResolvedValue({ items: [1, 2, 3] });
    const { result } = renderHook(() => useAsyncData(fetcher));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual({ items: [1, 2, 3] });
    expect(result.current.error).toBeNull();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("sets error on fetch failure", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("Network error"));
    const { result } = renderHook(() => useAsyncData(fetcher));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe("Network error");
  });

  it("sets error message for string errors", async () => {
    const fetcher = vi.fn().mockRejectedValue("Something went wrong");
    const { result } = renderHook(() => useAsyncData(fetcher));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe("Something went wrong");
  });

  it("sets fallback error message for unknown error types", async () => {
    const fetcher = vi.fn().mockRejectedValue(42);
    const { result } = renderHook(() => useAsyncData(fetcher));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe("An unknown error occurred");
  });

  it("refetch reloads data", async () => {
    let callCount = 0;
    const fetcher = vi.fn().mockImplementation(() => {
      callCount++;
      return Promise.resolve(`result-${callCount}`);
    });

    const { result } = renderHook(() => useAsyncData(fetcher));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBe("result-1");

    await act(async () => {
      result.current.refetch();
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBe("result-2");
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("refetch clears previous error", async () => {
    const fetcher = vi
      .fn()
      .mockRejectedValueOnce(new Error("First failure"))
      .mockResolvedValueOnce("success");

    const { result } = renderHook(() => useAsyncData(fetcher));

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe("First failure");

    await act(async () => {
      result.current.refetch();
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBeNull();
    expect(result.current.data).toBe("success");
  });

  it("re-fetches when dependencies change", async () => {
    const fetcher1 = vi.fn().mockResolvedValue("data-1");
    const fetcher2 = vi.fn().mockResolvedValue("data-2");

    const { result, rerender } = renderHook(({ dep, fn }) => useAsyncData(fn, [dep]), {
      initialProps: { dep: "a", fn: fetcher1 },
    });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBe("data-1");

    rerender({ dep: "b", fn: fetcher2 });

    await waitFor(() => {
      expect(result.current.data).toBe("data-2");
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it("does not re-fetch when dependencies stay the same", async () => {
    const fetcher = vi.fn().mockResolvedValue("data");

    const { rerender } = renderHook(({ dep }) => useAsyncData(fetcher, [dep]), {
      initialProps: { dep: "a" },
    });

    await waitFor(() => {
      expect(fetcher).toHaveBeenCalledTimes(1);
    });

    rerender({ dep: "a" });

    // fetcher should still have been called only once
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("aborts in-flight request on unmount", async () => {
    let capturedSignal: AbortSignal | undefined;
    const fetcher = vi.fn().mockImplementation(
      (options?: { signal?: AbortSignal }) =>
        new Promise<string>((resolve) => {
          capturedSignal = options?.signal;
          // Never resolves — simulates a long-running request
          setTimeout(() => resolve("done"), 10_000);
        }),
    );

    const { unmount } = renderHook(() => useAsyncData(fetcher));

    // Wait for the fetcher to be called
    await waitFor(() => {
      expect(fetcher).toHaveBeenCalledTimes(1);
    });

    expect(capturedSignal).toBeDefined();
    expect(capturedSignal!.aborted).toBe(false);

    unmount();

    expect(capturedSignal!.aborted).toBe(true);
  });

  it("aborts previous request when deps change", async () => {
    const signals: AbortSignal[] = [];
    const fetcher = vi.fn().mockImplementation((options?: { signal?: AbortSignal }) => {
      if (options?.signal) signals.push(options.signal);
      return Promise.resolve("data");
    });

    const { rerender } = renderHook(({ dep }) => useAsyncData(fetcher, [dep]), {
      initialProps: { dep: "a" },
    });

    await waitFor(() => {
      expect(fetcher).toHaveBeenCalledTimes(1);
    });

    rerender({ dep: "b" });

    await waitFor(() => {
      expect(fetcher).toHaveBeenCalledTimes(2);
    });

    // First signal should be aborted when deps changed
    expect(signals[0].aborted).toBe(true);
    // Second signal should still be active
    expect(signals[1].aborted).toBe(false);
  });

  it("sets loading to true during refetch", async () => {
    let resolvePromise: (value: string) => void;
    const fetcher = vi.fn().mockImplementation(
      () =>
        new Promise<string>((resolve) => {
          resolvePromise = resolve;
        }),
    );

    const { result } = renderHook(() => useAsyncData(fetcher));

    expect(result.current.loading).toBe(true);

    // Resolve first call
    await act(async () => {
      resolvePromise!("first");
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBe("first");

    // Trigger refetch - creates a new pending promise
    act(() => {
      result.current.refetch();
    });

    expect(result.current.loading).toBe(true);

    await act(async () => {
      resolvePromise!("second");
    });

    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBe("second");
  });
});
