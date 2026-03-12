SERVERS = {
    "math": {
        "transport": "stdio",
        "command":"uv",
        "args":[
            "run",
            "fastmcp",
            "run",
            "E:\\MCP-Client\\MathMCPserver.py"
        ]
    },
    "expense": {
        "transport":"streamable_http",
        "url":"https://exp.trk.mcp.malayjain.me/mcp"
    },
    "test-server": {
        "transport":"stdio",
        "command":"uv",
        "args":[
            "run",
            "fastmcp",
            "run",
            "E:\\Expense-tracker-MCP-Server\\main2.py"
        ]
    }
}