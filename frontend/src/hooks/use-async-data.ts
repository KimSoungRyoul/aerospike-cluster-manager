import { useState, useEffect, useCallback, useRef } from "react";
import { getErrorMessage } from "@/lib/utils";

interface UseAsyncDataResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export interface UseAsyncDataOptions {
  signal?: AbortSignal;
}

export function useAsyncData<T>(
  fetcher: (options?: UseAsyncDataOptions) => Promise<T>,
  deps: React.DependencyList = [],
): UseAsyncDataResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const fetcherRef = useRef(fetcher);
  const requestIdRef = useRef(0);
  const abortControllerRef = useRef<AbortController | null>(null);
  fetcherRef.current = fetcher;

  const fetch = useCallback(async () => {
    // Abort any in-flight request
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const requestId = ++requestIdRef.current;
    setLoading(true);
    setError(null);
    try {
      const result = await fetcherRef.current({ signal: controller.signal });
      if (requestIdRef.current === requestId) {
        setData(result);
      }
    } catch (err) {
      // Silently ignore aborted requests
      if (controller.signal.aborted) return;
      if (requestIdRef.current === requestId) {
        setError(getErrorMessage(err));
      }
    } finally {
      if (requestIdRef.current === requestId) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    fetch();
    return () => {
      requestIdRef.current++;
      abortControllerRef.current?.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, loading, error, refetch: fetch };
}
