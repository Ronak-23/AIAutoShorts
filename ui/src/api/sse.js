/**
 * ui/src/api/sse.js
 * =================
 * Reconnecting EventSource manager for live pipeline streaming.
 */

export function subscribeToRunEvents(runId, onEvent, onError) {
  const url = `/api/pipeline/runs/${runId}/events`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      onEvent(data);
    } catch (err) {
      console.error("[SSE] Failed to parse event data", err);
    }
  };

  eventSource.onerror = (err) => {
    if (onError) onError(err);
  };

  return () => {
    eventSource.close();
  };
}
