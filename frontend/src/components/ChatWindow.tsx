import { useRef, useState } from "react";
import InputBar from "./InputBar";
import { streamRespond } from "../lib/api";
import { useEffect } from "react";

type Msg =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "assistant"; text: string; done?: boolean };

type ChatWindowProps = {
  onFinal?: (payload: Record<string, unknown>) => void;
  hideInput?: boolean;
  onSendExternal?: (send: (text: string) => Promise<void>) => void;
  onAssistantChange?: (text: string) => void;  
};

export default function ChatWindow({ onFinal, onSendExternal, hideInput, onAssistantChange }: ChatWindowProps) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const addUser = (text: string) => setMessages((m) => [...m, { id: crypto.randomUUID(), role: "user", text }]);
  const startAssistant = () => {
    const id = crypto.randomUUID();
    setMessages((m) => [...m, { id, role: "assistant", text: "", done: false }]);
    return id;
  };
  const appendToAssistant = (id: string, delta: string) => {
    setMessages((m) => {
      const next = m.map((msg) =>
        msg.id === id && msg.role === "assistant"
          ? { ...msg, text: msg.text + delta }
          : msg
      );
      const last = next[next.length - 1];
      if (last?.role === "assistant") onAssistantChange?.(last.text);
      return next;
    });
  };

  const finishAssistant = (id: string) =>
    setMessages((m) => {
      const next = m.map((msg) =>
        msg.id === id && msg.role === "assistant" ? { ...msg, done: true } : msg
      );
      const last = next[next.length - 1];
      if (last?.role === "assistant") onAssistantChange?.(last.text);
      return next;
    });


  const handleSend = async (text: string) => {
    if (abortRef.current) { abortRef.current.abort(); abortRef.current = null; }
    addUser(text);
    const aId = startAssistant();
    setBusy(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamRespond(text, {
        signal: controller.signal,
        onToken: (t) => appendToAssistant(aId, t),
        onFinal: (payload) => { finishAssistant(aId); onFinal?.(payload); },
        onError: (msg) => { appendToAssistant(aId, `\n[eroare] ${msg}`); finishAssistant(aId); },
      });
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  };

  useEffect(() => {
    if (onSendExternal) onSendExternal(handleSend);
  }, [onSendExternal]);
  
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  return (
    <div className="chat">
      {messages.length === 0 && (
        <div style={{ fontSize: 14, color: "var(--muted)" }}>
          Începe cu o întrebare, de ex. „Recomandă-mi o carte fantasy despre prietenie.”
        </div>
      )}
      {messages.map((m) => (
        <div key={m.id} className={`bubble ${m.role}`}>
          {m.text}
          {m.role === "assistant" && !m.done ? <span className="typing-caret" /> : null}
        </div>
      ))}
      {!hideInput && <InputBar onSend={handleSend} disabled={busy} />}
      <div ref={endRef} />
    </div>
  );
}
