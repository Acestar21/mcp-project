import { AgentEvent } from "../AgentEvent"
import { useState , useEffect } from "react"

type Props = {
    events: AgentEvent[]
    visible: boolean
}


export function DebugSidebar({ events, visible }: Props) {
    if (!visible) return null
    
    useEffect(() => {
        const last = events[events.length - 1]
        if (last?.type === "request_started") {
            setOpenRequests(prev => ({
            ...prev,
            [last.request_id]: true,
            }))
        }
    }, [events])
    const [openRequests, setOpenRequests] = useState<Record<string, boolean>>({})

    const toggleRequest = (id: string) => {
        setOpenRequests(prev => ({
            ...prev,
            [id]: !prev[id],
        }))
    }

    const eventsByRequest = events.reduce<Record<string, AgentEvent[]>>(
        (acc, event) => {
            if (!acc[event.request_id]) {
                acc[event.request_id] = []
            }
            acc[event.request_id].push(event)
            return acc
        },
        {}
    )

    return (
        <div
        style={{
            height: "100%",
            display: "flex",
            flexDirection: "column",
            padding: 10,
            fontSize: 12,
            background: "#fafafa",
        }}
        >
        <strong>Debug Events</strong>

        <div style={{ flex: 1, overflowY: "auto", marginTop: 8 }}>
            {Object.entries(eventsByRequest).map(([requestId, reqEvents]) => {
            const isOpen = openRequests[requestId]

            return (
                <div key={requestId} style={{ marginBottom: 12 }}>
                <div
                    style={{
                    cursor: "pointer",
                    fontWeight: "bold",
                    borderBottom: "1px solid #ddd",
                    paddingBottom: 4,
                    }}
                    onClick={() => toggleRequest(requestId)}
                >
                    {isOpen ? "▾" : "▸"} Request {requestId.slice(0, 8)}
                </div>

                {isOpen && (
                    <div style={{ marginLeft: 8, marginTop: 6 }}>
                    {reqEvents.map((e, idx) => {
                        if (
                        e.type !== "tool_call_started" &&
                        e.type !== "tool_call_succeeded" &&
                        e.type !== "tool_call_failed" &&
                        e.type !== "policy_blocked" &&
                        e.type !== "request_failed"
                        ) {
                        return null
                        }

                        let color = "#333"
                        if (
                        e.type === "tool_call_failed" ||
                        e.type === "request_failed"
                        ) {
                        color = "red"
                        }
                        if (e.type === "tool_call_succeeded") {
                        color = "green"
                        }

                        return (
                        <div key={idx} style={{ marginTop: 6, color }}>
                            <div><strong>{e.type}</strong></div>
                            {e.tool && <div>Tool: {e.tool}</div>}
                            {e.error && <div>Error: {e.error}</div>}
                            {e.reason && <div>Reason: {e.reason}</div>}
                        </div>
                        )
                    })}
                    </div>
                )}
                </div>
            )
            })}
        </div>
        </div>
    )
    }