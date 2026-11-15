"use client";
import { useCallback, useEffect, useState } from "react";
import { api, ApiFail } from "./api";

/** Fetch JSON from the API with loading / error state. Pass null to skip. */
export function useFetch<T>(path: string | null, timeoutMs = 20000) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiFail | null>(null);
  const [loading, setLoading] = useState(!!path);
  const [tick, setTick] = useState(0);
  const reload = useCallback(() => setTick((t) => t + 1), []);

  useEffect(() => {
    if (!path) { setLoading(false); return; }
    let live = true;
    setLoading(true); setError(null);
    api<T>(path, { timeoutMs })
      .then((d) => { if (live) { setData(d); setLoading(false); } })
      .catch((e) => { if (live) { setError(e as ApiFail); setLoading(false); } });
    return () => { live = false; };
  }, [path, tick, timeoutMs]);

  return { data, error, loading, reload };
}
