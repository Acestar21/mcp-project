import { AgentEvent } from "../AgentEvent"

type Props = {
    events: AgentEvent[]
    visible: boolean
}

export function DebugSidebar({ events, visible }: Props) {
    if (!visible) return null

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
        <div style={{ flex: 1, overflowY: "auto", marginTop: 8 , marginBottom: 15}}>
        {events.map((e, idx) => {
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
            if (e.type === "tool_call_failed" || e.type === "request_failed") {
            color = "red"
            }
            if (e.type === "tool_call_succeeded") {
            color = "green"
            }

            return (
            <div key={idx} style={{ marginTop: 8, color }}>
                <div><strong>{e.type}</strong></div>

                {e.tool && <div>Tool: {e.tool}</div>}
                {e.error && <div>Error: {e.error}</div>}
                {e.reason && <div>Reason: {e.reason}</div>}
            </div>
            )
        })}
        </div>
    </div>
    )
}
