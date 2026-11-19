import { useEffect, useState } from "react";

import { getJob } from "./api.js";

const POLL_INTERVAL_MS = 1000;

// Follows a job until it is completed, refreshing it every second so the
// table shows each file moving from pending to processing to done/failed.
export function useJob(jobId) {
  const [job, setJob] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setJob(null);
    setError("");
    if (!jobId) return undefined;

    let cancelled = false;
    let timer;

    async function poll() {
      try {
        const latest = await getJob(jobId);
        if (cancelled) return;
        setJob(latest);
        if (latest.status !== "completed") {
          timer = setTimeout(poll, POLL_INTERVAL_MS);
        }
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    }

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [jobId]);

  return { job, error };
}
