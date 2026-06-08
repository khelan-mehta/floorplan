import { useEffect, useState } from 'react';
import { jobWebsocketUrl } from '../api/client';

export interface JobEvent {
  status: string;
  progress?: number;
  plan_id?: string;
  result?: { plan_ids?: string[] };
  error?: string;
}

/** Subscribe to a job's progress over WebSocket. Returns the latest event + connection state. */
export function useJob(jobId: string | null): { event: JobEvent | null; connected: boolean } {
  const [event, setEvent] = useState<JobEvent | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!jobId) return;
    const ws = new WebSocket(jobWebsocketUrl(jobId));
    ws.onopen = () => setConnected(true);
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data as string) as JobEvent;
        if (data.status !== 'heartbeat') setEvent(data);
      } catch {
        /* ignore malformed frames */
      }
    };
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    return () => ws.close();
  }, [jobId]);

  return { event, connected };
}
