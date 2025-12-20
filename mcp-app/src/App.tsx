import { useReducer , useEffect , useState } from 'react'
import { eventReducer , initialEventState } from './eventStore'
import { ChatView } from './component/ChatWindow';
import { listen } from "@tauri-apps/api/event"
import { invoke } from '@tauri-apps/api/core';




function App() {

  const [state, dispatch] = useReducer(
    eventReducer,
    initialEventState
  )

  useEffect(() => {
    const unlistenPromise = listen<string>("agent_event", (event) => {
      try {
        const envelope = JSON.parse(event.payload)
        const data = envelope.content

        if (data?.type && data?.request_id && data?.timestamp) {
          dispatch({ type: "ADD_EVENT", event: data })
        }
      } catch (e) {
        console.error("Invalid agent event", e)
      }
    })

    return () => {
      unlistenPromise.then((unlisten) => unlisten())
    }
  }, [])



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

  const activeRequestId = getActiveRequestId()
  const isBusy = activeRequestId !== null


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
  useEffect(() => { console.log("EVENTS:", state.events) }, [state.events])

return (
  <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
    {/* Center chat */}
    <div style={{ flex: 1, overflowY: "auto", borderBottom: "1px solid #ddd" }}>
      <ChatView events={state.events} />
    </div>

    {/* Footer */}
    <div style={{ padding: 12 }}>
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={onKeyDown}
        disabled={isBusy}
        placeholder={isBusy ? "Agent is busy…" : "Type a message"}
        rows={3}
        style={{ width: "100%" }}
      />
      <button
        onClick={sendQuery}
        disabled={isBusy || !input.trim()}
      >
        {isBusy ? "Working…" : "Send"}
      </button>
    </div>
  </div>
)
}

export default App