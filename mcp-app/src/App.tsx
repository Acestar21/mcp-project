// mcp-app/src/App.tsx
import { useEffect, useState, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen, UnlistenFn } from "@tauri-apps/api/event";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { dracula } from "react-syntax-highlighter/dist/esm/styles/prism";
import TextareaAutosize from "react-textarea-autosize";

interface Message {
  role: "user" | "assistant" | "system" | "error";
  content: string;
}

// NEW: Define the shape of messages coming from Python
interface PythonEvent {
  type?: "status" | "response";
  content?: string;
  ok?: boolean;
  response?: string;
  error?: string;
  trace?: string;
}

export default function App() {
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  // NEW: State to hold the live "Thinking..." updates
  const [status, setStatus] = useState(""); 
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading, status]);

  useEffect(() => {
    let unlistenFunction: UnlistenFn | undefined;
    let isMounted = true;

    const setupListener = async () => {
      const unlisten = await listen<string>("python-output", (event) => {
        if (!isMounted) return;

        const text = event.payload;
        try {
          // Parse the incoming JSON from bridge.py
          const parsed: PythonEvent = JSON.parse(text);

          // CASE 1: Status Update (The "Thinking" broadcasts)
          // We check for type === "status" so we don't treat it as an error
          if (parsed.type === "status" && parsed.content) {
             setStatus(parsed.content);
             return; // Don't stop loading, just update text
          }

          // CASE 2: Final Response (The actual answer)
          // We also support the old format (no 'type') just in case
          if (parsed.type === "response" || parsed.ok !== undefined) {
            setIsLoading(false); // Enable the button again
            setStatus("");       // Clear the status text

            if (parsed.ok) {
              setMessages((prev) => [...prev, { role: "assistant", content: parsed.response || "" }]);
            } else {
              setMessages((prev) => [...prev, { role: "error", content: JSON.stringify(parsed) }]);
            }
          }

        } catch {
          // Fallback for non-JSON output (should be rare now)
        }
      });

      unlistenFunction = unlisten;
    };

    setupListener();

    return () => {
      isMounted = false;
      if (unlistenFunction) {
        unlistenFunction();
      }
    };
  }, []);

  async function sendQuery() {
    if (!query.trim() || isLoading) return;

    const currentQuery = query;
    setMessages((prev) => [...prev, { role: "user", content: currentQuery }]);
    setQuery("");
    setIsLoading(true);
    setStatus("Starting..."); // Initial status

    try {
      await invoke("send_to_python", { query: currentQuery });
    } catch (error) {
      setMessages((prev) => [...prev, { role: "error", content: `Failed to send: ${error}` }]);
      setIsLoading(false);
      setStatus("");
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
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
          backgroundColor: "#1e1e1e",
          display: "flex",
          flexDirection: "column",
          gap: "15px",
        }}
      >
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "85%",
              padding: "12px",
              borderRadius: "8px",
              backgroundColor:
                msg.role === "user"
                  ? "#007bff"
                  : msg.role === "error"
                  ? "#ff4444"
                  : "#2d2d2d",
              color: "white",
              boxShadow: "0 2px 4px rgba(0,0,0,0.2)"
            }}
          >
            <div style={{ fontSize: "0.8em", opacity: 0.7, marginBottom: "6px", fontWeight: "bold" }}>
              {msg.role.toUpperCase()}
            </div>
            
<Markdown
              remarkPlugins={[remarkGfm]}
              components={{
                code(props) {
                  // FIX: Destructure 'ref' here so it is NOT included in 'rest'
                  const { children, className, node, ref, ...rest } = props;
                  const match = /language-(\w+)/.exec(className || "");
                  return match ? (
                    <SyntaxHighlighter
                      {...rest}
                      children={String(children).replace(/\n$/, "")}
                      style={dracula}
                      language={match[1]}
                      PreTag="div"
                    />
                  ) : (
                    <code {...rest} className={className} style={{backgroundColor: '#444', padding: '2px 4px', borderRadius: '4px'}}>
                      {children}
                    </code>
                  );
                },
              }}
            >
              {msg.content}
            </Markdown>
          </div>
        ))}
        
        {/* NEW STATUS INDICATOR (The Green Text) */}
        {isLoading && (
            <div style={{ 
                alignSelf: 'flex-start', 
                color: '#00ff88',  // Matrix green
                fontFamily: 'monospace',
                fontSize: '0.9em',
                padding: '10px',
                borderLeft: '2px solid #00ff88',
                backgroundColor: 'rgba(0, 255, 136, 0.1)',
                marginLeft: '10px' 
            }}>
                {status || "Assistant is thinking..."}
            </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div style={{ display: "flex", gap: "10px", alignItems: "flex-end" }}>
        <TextareaAutosize
          minRows={1}
          maxRows={6}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          style={{
            flex: 1,
            padding: "12px",
            borderRadius: "6px",
            border: "1px solid #ccc",
            fontSize: "16px",
            resize: "none",
            fontFamily: "inherit"
          }}
        />
        <button
          onClick={sendQuery}
          disabled={isLoading}
          style={{
            padding: "12px 24px",
            borderRadius: "6px",
            border: "none",
            backgroundColor: isLoading ? "#6c757d" : "#007bff",
            color: "white",
            cursor: isLoading ? "default" : "pointer",
            fontSize: "16px",
            fontWeight: "bold",
            height: "45px"
          }}
        >
          {isLoading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
}