
import { useRef, useState } from "react";
import ChatWindow from "./components/ChatWindow";
import BookCard from "./components/BookCard";
import InputBar from "./components/InputBar";

export default function App() {
  const [book, setBook] = useState<{ title?: string; why?: string; summary?: string } | null>(null);
  const [lastAssistant, setLastAssistant] = useState("");     
  const [speaking, setSpeaking] = useState(false);            
  const sendRef = useRef<null | ((text: string) => Promise<void>)>(null);
  const utterRef = useRef<SpeechSynthesisUtterance | null>(null);

  const handleSpeak = () => {
    const synth = window.speechSynthesis;
    if (!synth) return;

    if (speaking) {
      synth.cancel();
      setSpeaking(false);
      utterRef.current = null;
      return;
    }

    const text = lastAssistant?.trim();
    if (!text) return;

    const u = new SpeechSynthesisUtterance(text);
    u.lang = "ro-RO";      
    u.rate = 1.0;         
    u.pitch = 1.0;         
    u.onend = () => { setSpeaking(false); utterRef.current = null; };
    u.onerror = () => { setSpeaking(false); utterRef.current = null; };
    utterRef.current = u;
    setSpeaking(true);
    synth.speak(u);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-inner">
          <div className="brand">
            <div className="brand-logo">SL</div>
            <h1>Smart Library</h1>
          </div>
        </div>
      </header>


      <main className="page">
        <div className={`bookdrawer ${book ? "open" : ""}`}>
          {book && (
            <div className="container">
              <div className="bookpanel" style={{ padding: 0 }}>
                <BookCard title={book.title} why={book.why} summary={book.summary} />
                <button
                  onClick={() => setBook(null)}
                  aria-label="Închide"
                  style={{ float: "right", border: "none", background: "transparent", cursor: "pointer", fontSize: 18 }}
                >
                  ×
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="container">
          <ChatWindow
            hideInput
            onSendExternal={(send) => { sendRef.current = send; }}
            onAssistantChange={(t) => setLastAssistant(t)}  
            onFinal={(payload) => {
              if (payload?.recommendation || payload?.summary) {
                setBook({
                  title: (payload.recommendation as any)?.title,
                  why: (payload.recommendation as any)?.why,
                  summary: (payload as any)?.summary,
                });
              }
            }}
          />
        </div>

        <div className="footer-input">
          <div className="container">
            <InputBar
              speaking={speaking}
              onSpeak={handleSpeak}                 
              onSend={(msg) => (sendRef.current ? sendRef.current(msg) : Promise.resolve())}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
