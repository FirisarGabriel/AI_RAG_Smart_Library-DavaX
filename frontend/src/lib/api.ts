
// Minimal SSE client for the Smart Library frontend.
// Uses fetch() + ReadableStream to consume Server-Sent Events from /respond.
//
// Env:
//   VITE_API_URL=http://127.0.0.1:8000

export type FinalPayload = { final: true } & Record<string, unknown>;

export type StreamHandlers = {
  onToken?: (text: string) => void;
  onFinal?: (payload: FinalPayload) => void;
  onError?: (message: string) => void;
  signal?: AbortSignal; 
};

const API_BASE =
  (import.meta as any).env?.VITE_API_URL?.replace(/\/+$/, "") ||
  "http://127.0.0.1:8000";

export async function healthz(): Promise<boolean> {
  try {
    const r = await fetch(`${API_BASE}/healthz`, { method: "GET" });
    return r.ok;
  } catch {
    return false;
  }
}

export async function streamRespond(
  message: string,
  handlers: StreamHandlers = {}
): Promise<void> {
  const { onToken, onFinal, onError, signal } = handlers;

  const res = await fetch(`${API_BASE}/respond`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
    signal,
  });

  if (!res.ok || !res.body) {
    const msg = `Request failed (${res.status})`;
    onError?.(msg);
    throw new Error(msg);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let idx: number;
      while ((idx = buffer.indexOf("\n\n")) !== -1) {
        const rawEvent = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        handleSSEFrame(rawEvent, { onToken, onFinal, onError });
      }
    }

    if (buffer.trim().length > 0) {
      handleSSEFrame(buffer, { onToken, onFinal, onError });
      buffer = "";
    }
  } catch (e: any) {
    if (e?.name === "AbortError") return;
    onError?.(String(e?.message || e));
    throw e;
  } finally {
    try {
      reader.releaseLock();
    } catch {
    }
  }
}

function handleSSEFrame(
  rawEvent: string,
  handlers: Omit<StreamHandlers, "signal">
) {
  const { onToken, onFinal, onError } = handlers;

  let eventType = "message";
  const dataLines: string[] = [];

  for (const line of rawEvent.split("\n")) {
    if (line.startsWith("event:")) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice(6));
    }
  }

  const data = dataLines.join("\n");

  switch (eventType) {
    case "token": {
      if (data) onToken?.(data);
      break;
    }
    case "final": {
      try {
        const payload = data ? (JSON.parse(data) as FinalPayload) : ({ final: true } as FinalPayload);
        onFinal?.(payload);
      } catch {
        onFinal?.({ final: true, raw: data } as FinalPayload);
      }
      break;
    }
    case "error": {
      try {
        const payload = data ? JSON.parse(data) : null;
        const msg = payload?.error ?? data ?? "Unknown error";
        onError?.(msg);
      } catch {
        onError?.(data || "Unknown error");
      }
      break;
    }
    default: {
      break;
    }
  }
}

/**
 * Convenience wrapper for a one-off, non-streaming style usage.
 * Accumulates tokens into a single string and resolves on "final".
 */
export async function requestRespond(
  message: string,
  opts: { signal?: AbortSignal } = {}
): Promise<{ text: string; final: FinalPayload | null }> {
  let acc = "";
  let final: FinalPayload | null = null;
  await streamRespond(message, {
    signal: opts.signal,
    onToken: (t) => {
      acc += t;
    },
    onFinal: (p) => {
      final = p;
    },
  });
  return { text: acc, final };
}
