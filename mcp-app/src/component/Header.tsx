import { AgentEvent } from "../AgentEvent";

type Props = {
    events: AgentEvent[];
}

function getAgentStatus(events: AgentEvent[]){
    for ( let i = events.length - 1; i >= 0 ; i-- ){
        const e = events[i]

        if (e.type === "request_failed" || e.type === "tool_call_failed") {
            return "Error"
        }

        if (e.type === "tool_call_started") {
            return "Executing"
        }

        if (e.type === "planning_started") {
            return "Thinking"
        }

        if (e.type === "request_completed") {
            return "Idle"
        }        
    }
    return "Idle"
}

export function Header({ events }: Props) {
    const status = getAgentStatus(events)
    return (
    <div
        style={{
            height: 48,
            padding: "0 12px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: "1px solid #ddd",
            fontSize: 14,
        }}
        >
        {/* Left: Status */}
        <div>
            <strong>Status:</strong> {status}
        </div>

        {/* Right: Connection */}
        <div style={{ color: "green" }}>
            ● Connected
        </div>
    </div>
    )
}