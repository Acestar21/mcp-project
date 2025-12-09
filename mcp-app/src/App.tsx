import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

export default function App() {
  const [query, setQuery] = useState("");
  const [output, setOutput] = useState("");

  async function sendQuery() {
    try {
      const raw = await invoke<string>("send_to_python", { query });
      // raw is a JSON line returned by bridge.py e.g. {"ok":true,"response":"..."}
      try {
        const parsed = JSON.parse(raw);
        if (parsed.ok) {
          setOutput(typeof parsed.response === "string" ? parsed.response : JSON.stringify(parsed.response, null, 2));
        } else {
          setOutput("Error: " + (parsed.error || JSON.stringify(parsed)));
        }
      } catch (e) {
        setOutput("Non-JSON response: " + raw);
      }
    } catch (err) {
      setOutput("Invoke error: " + String(err));
    }
  }

  return (
    <div style={{ padding: 20 }}>
      <h3>MCP Bridge Test</h3>
      <input value={query} onChange={(e) => setQuery(e.target.value)} style={{ width: "60%" }} />
      <button onClick={sendQuery} style={{ marginLeft: 8 }}>Send</button>
      <pre style={{ whiteSpace: "pre-wrap", marginTop: 12 }}>{output}</pre>
    </div>
  );
}