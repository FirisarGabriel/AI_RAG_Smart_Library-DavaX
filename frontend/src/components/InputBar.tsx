
import { useState } from "react";

type Props = {
  onSend: (text: string) => void | Promise<void>;
  disabled?: boolean;
  onSpeak?: () => void;    
  speaking?: boolean;       
};

export default function InputBar({ onSend, disabled, onSpeak, speaking }: Props) {
  const [text, setText] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const t = text.trim();
    if (!t) return;
    onSend(t);
    setText("");
  };

  return (
    <form className="inputbar" onSubmit={submit}>
      <input
        type="text"
        placeholder="Scrie un mesaj..."
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={disabled}
      />
      {/* TTS */}
      <button
        type="button"
        className="iconbtn"
        onClick={onSpeak}
        title={speaking ? "Oprește citirea" : "Ascultă ultimul răspuns"}
      >
        {speaking ? "■" : "🔊"}
      </button>
      <button type="submit" disabled={disabled}>Trimite</button>
    </form>
  );
}
