import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

type Message = {
  role: "user" | "assistant";
  text: string;
};

export default function App() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);

  async function sendQuery() {
    if (!query.trim()) return;

    // Add user message to chat
    setMessages((prev) => [...prev, { role: "user", text: query }]);

    try {
      const raw = await invoke<string>("send_to_python", { query });

      let text = "";
      try {
        const parsed = JSON.parse(raw);
        if (parsed.ok) {
          text = typeof parsed.response === "string"
            ? parsed.response
            : JSON.stringify(parsed.response, null, 2);
        } else {
          text = "Error: " + (parsed.error || JSON.stringify(parsed));
        }
      } catch (e) {
        text = "Non-JSON response: " + raw;
      }

      // Add assistant message
      setMessages((prev) => [...prev, { role: "assistant", text }]);

    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Invoke error: " + String(err) }
      ]);
    }

    setQuery(""); // clear textbox
  }

  return (
    <div style={{ padding: 20 }}>
      <h3>MCP App</h3>

      {/* Chat window */}
      <div
        style={{
          height: "70vh",
          overflowY: "auto",
          border: "1px solid #444",
          padding: 10,
          marginBottom: 20,
          borderRadius: 8,
        }}
      >
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              marginBottom: 12,
              textAlign: msg.role === "user" ? "right" : "left",
            }}
          >
            <strong>{msg.role === "user" ? "You" : "Assistant"}:</strong>
            <pre style={{ whiteSpace: "pre-wrap" }}>{msg.text}</pre>
          </div>
        ))}
      </div>

      {/* Input box */}
      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        style={{ width: "60%" }}
      />

      <button onClick={sendQuery} style={{ marginLeft: 8 }}>
        Send
      </button>
    </div>
  );
}