// === Request DTO (mirror of backend/app/types.py: ChatRequest) ===
export type ChatRequest = {
  message: string;
};

// === SSE stream events (contract din backend) ===
export type StreamEventToken = {
  type: "token";
  text: string;
};

export type StreamEventFinal = {
  type: "final";
  payload: FinalResponse;
};

export type StreamEventError = {
  type: "error";
  error: string;
};

export type StreamEvent = StreamEventToken | StreamEventFinal | StreamEventError;

// === Final payload (mirror of backend/app/types.py: FinalResponse) ===
export type FinalResponse = {
  final: true;
  recommendation?: {
    title?: string;
    why?: string;
    [k: string]: unknown;
  } | null;
  summary?: string | null;
  [k: string]: unknown;
};

// === UI-level message model ===
export type ChatMessage =
  | { role: "user"; text: string; id: string }
  | { role: "assistant"; text: string; id: string; done?: boolean };
