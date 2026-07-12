"""Public MCP server constants."""

PUBLIC_SERVER_NAME = "plwc-gateway"
FORBIDDEN_PUBLIC_SERVER_NAMES = frozenset(
    {
        "plfc",
        "plfc-mcp",
        "pba-mcp",
        "desktop-commander",
        "desktop-commander-hardened",
    }
)
