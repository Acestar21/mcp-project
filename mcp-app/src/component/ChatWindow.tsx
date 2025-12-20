import { AgentEvent } from "../AgentEvent";


type Props = {
    events: AgentEvent[];
}

export function ChatView({ events }: Props) {
    return (
        <div style = {{padding: 12}}>
            {events.map((e , index) => {
                if (e.type === "request_started") {
                    return (
                        <div key={index} style={{ marginBottom: 10 }}>
                        <strong>You:</strong> {e.query}
                        </div>
                    )
            }

            if (e.type === "assistant_message") {
                return (
                    <div key={index} style={{ marginBottom: 10 }}>
                        <strong>Assistant:</strong> {e.content}
                    </div>
                )
            }

            if (e.type === "planning_started") {
                return (
                    <div key={index} style={{ fontStyle: "italic", opacity: 0.6 }}>
                        🤔 Thinking…
                    </div>
                )
            }

            if (e.type === "tool_call_started") {
            return (
                <div key={index} style={{ fontStyle: "italic", opacity: 0.6 }}>
                ⚙️ Executing {e.tool}…
                </div>
            )
            }

            return null
        })}
        </div>
    )
}