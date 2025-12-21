type Capabilities = {
    [serverName: string]: {
        tool_count: number
        tools: string[]
    }
}

type ToolsSidebarProps = {
    capabilities: Capabilities | null
}

export function ToolsSidebar({ capabilities }: ToolsSidebarProps) {
    return (
        <div className="tools-sidebar">
        <h3>Tools</h3>

        {!capabilities && (
            <div className="muted">Loading tools…</div>
        )}

        {capabilities &&
            Object.entries(capabilities).map(([server, info]) => (
            <div key={server} className="server-block">
                <div className="server-name">
                {server} ({info.tool_count})
                </div>

                <ul className="tool-list">
                {info.tools.map(tool => (
                    <li key={tool}>{tool}</li>
                ))}
                </ul>
            </div>
            ))}
        </div>
    )
}
