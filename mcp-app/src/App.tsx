import { useEffect, useState, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, UnlistenFn } from "@tauri-apps/api/event";

interface Message {
  role: "user" | "assistant" | "system" | "error";
  content: string;
}

export default function App() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 1. Auto-scroll to bottom when messages change
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // 2. Setup Event Listener (ROBUST FIX FOR DUPLICATES)
  useEffect(() => {
    let unlistenFunction: UnlistenFn | undefined;
    let isMounted = true;

    // Create the listener
    const setupListener = async () => {
      const unlisten = await listen<string>("python-output", (event) => {
        if (!isMounted) return; // Ignore events if component is unmounted

        const text = event.payload;
        try {
          const parsed = JSON.parse(text);
          if (parsed.ok) {
            setMessages((prev) => [...prev, { role: "assistant", content: parsed.response }]);
          } else {
            setMessages((prev) => [...prev, { role: "error", content: JSON.stringify(parsed) }]);
          }
        } catch {
          setMessages((prev) => [...prev, { role: "system", content: text }]);
        }
      });

      unlistenFunction = unlisten;

      // If the component unmounted while we were waiting for the promise, clean up immediately
      if (!isMounted) {
        unlisten();
      }
    };

    setupListener();

    // Cleanup function
    return () => {
      isMounted = false;
      if (unlistenFunction) {
        unlistenFunction();
      }
    };
  }, []);

  async function sendQuery() {
    if (!query.trim()) return;

    const currentQuery = query;
    // Optimistic UI update: Show user message immediately
    setMessages((prev) => [...prev, { role: "user", content: currentQuery }]);
    setQuery("");

    try {
      await invoke("send_to_python", { query: currentQuery });
    } catch (error) {
      setMessages((prev) => [...prev, { role: "error", content: `Failed to send: ${error}` }]);
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      sendQuery();
    }
  };

  return (
    <div style={{ padding: 20, maxWidth: "800px", margin: "0 auto", fontFamily: "sans-serif" }}>
      <h3>MCP Chat Client</h3>

      <div
        style={{
          height: "500px",
          overflowY: "auto",
          border: "1px solid #ccc",
          borderRadius: "8px",
          padding: "15px",
          marginBottom: "15px",
          backgroundColor: "#f9f9f9",
          display: "flex",
          flexDirection: "column",
          gap: "10px",
        }}
      >
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "80%",
              padding: "10px",
              borderRadius: "8px",
              backgroundColor:
                msg.role === "user"
                  ? "#007bff"
                  : msg.role === "error"
                  ? "#ffcccc"
                  : "#e1e1e1",
              color: msg.role === "user" ? "white" : "black",
              whiteSpace: "pre-wrap",
              boxShadow: "0 1px 2px rgba(0,0,0,0.1)"
            }}
          >
            <div style={{ fontSize: "0.8em", opacity: 0.7, marginBottom: "4px" }}>
              {msg.role === "user" ? "You" : "Assistant"}
            </div>
            <div>{msg.content}</div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div style={{ display: "flex", gap: "10px" }}>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          style={{
            flex: 1,
            padding: "12px",
            borderRadius: "4px",
            border: "1px solid #ccc",
            fontSize: "16px"
          }}
        />
        <button
          onClick={sendQuery}
          style={{
            padding: "10px 24px",
            borderRadius: "4px",
            border: "none",
            backgroundColor: "#007bff",
            color: "white",
            cursor: "pointer",
            fontSize: "16px",
            fontWeight: "bold"
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}