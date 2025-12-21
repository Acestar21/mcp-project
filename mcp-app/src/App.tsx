import { useReducer, useEffect, useState } from "react"
import { eventReducer, initialEventState } from "./eventStore"
import { ChatView } from "./component/ChatWindow"
import { listen } from "@tauri-apps/api/event"
import { invoke } from "@tauri-apps/api/core"
import { Header } from "./component/Header"
import { DebugSidebar } from "./component/DebugSidebar"
import { ToolsSidebar } from "./component/ToolSidebar"
/* ---------------- Types ---------------- */

type Capabilities = {
  [serverName: string]: {
    tool_count: number
    tools: string[]
  }
}

type CapabilitiesPayload = {
  type: "capabilities"
  servers: Capabilities
}

/* ---------------- App ---------------- */

function App() {
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null)
  const [showTools, setShowTools] = useState(true)

  const [state, dispatch] = useReducer(
    eventReducer,
    initialEventState
  )

  const [showDebug, setShowDebug] = useState(false)

  /* -------- Agent Events -------- */
  useEffect(() => {
    const unlistenPromise = listen<any>("agent_event", (event) => {
      const data = event.payload

      if (
        data?.type &&
        data?.request_id &&
        data?.timestamp
      ) {
        dispatch({ type: "ADD_EVENT", event: data })
      }
    })

    return () => {
      unlistenPromise.then(unlisten => unlisten())
    }
  }, [])

  /* -------- Capabilities -------- */
  useEffect(() => {
    const unlistenPromise = listen<CapabilitiesPayload>(
      "capabilities",
      (event) => {
        setCapabilities(event.payload.servers)
        console.log("Capabilities loaded:", event.payload.servers)
      }
    )

    return () => {
      unlistenPromise.then(unlisten => unlisten())
    }
  }, [])

  /* -------- Busy State -------- */
  const getActiveRequestId = () => {
    for (let i = state.events.length - 1; i >= 0; i--) {
      const e = state.events[i]
      if (e.type === "request_completed" || e.type === "request_failed") {
        return null
      }
      if (e.type === "request_started") {
        return e.request_id
      }
    }
    return null
  }

  const isBusy = getActiveRequestId() !== null

  /* -------- Input -------- */
  const [input, setInput] = useState("")

  const sendQuery = async () => {
    if (!input.trim() || isBusy) return

    try {
      await invoke("send_to_python", { query: input })
      setInput("")
    } catch (e) {
      console.error("Failed to send query", e)
    }
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendQuery()
    }
  }

  useEffect(() => {
    console.log("CAPABILITIES STATE:", capabilities)
  }, [capabilities])

  /* -------- Render -------- */
  return (
    <div className="app-root">
        <div className={`tools-sidebar-container ${showTools ? "open" : ""}`}>
          <ToolsSidebar capabilities={capabilities} />
        </div>


      <div
        className={`main-column 
          ${showDebug ? "debug-open" : ""} 
          ${showTools ? "tools-open" : ""}`}
      >
        <Header events={state.events} />

        <div className="chat-area">
          <ChatView events={state.events} />
        </div>

        <div className="footer">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            disabled={isBusy}
            placeholder={isBusy ? "Agent is busy…" : "Type a message"}
            rows={3}
          />

          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <button onClick={sendQuery} disabled={isBusy || !input.trim()}>
              {isBusy ? "Working…" : "Send"}
            </button>
            <button onClick={() => setShowTools(v => !v)}>
              🛠
            </button>
            <button onClick={() => setShowDebug(v => !v)}>☰</button>
          </div>
        </div>
      </div>

      <div className={`debug-sidebar-container ${showDebug ? "open" : ""}`}>
        <DebugSidebar events={state.events} visible={showDebug} />
      </div>
    </div>
  )
}

export default App
