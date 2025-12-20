export type AgentEvent = {
    type: string
    request_id: string
    timestamp: number
    [key: string]: any

    query?: string
    content?: string
    tool?: string
    args?: any
    intent?: string
    tool_count?: number
    tools?: string[]
    step?: number
    max_steps?: number
    error?: string
    reason?: string
}