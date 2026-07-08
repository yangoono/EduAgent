import os
import sqlite3
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, CallToolRequest

# Initialize MCP Server
app = Server("EduAgent-MCP-Server")

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "teachsys.db")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools for this MCP Server"""
    return [
        Tool(
            name="query_edu_database",
            description="执行 SQLite SQL 语句查询教务系统数据库（包含 students, courses, score 等表）",
            inputSchema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "合法的 SQLite SELECT 语句"
                    }
                },
                "required": ["sql"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool execution requests"""
    if name != "query_edu_database":
        raise ValueError(f"未知工具: {name}")

    sql = arguments.get("sql")
    if not sql:
        raise ValueError("缺少 sql 参数")

    if "delete" in sql.lower() or "update" in sql.lower() or "insert" in sql.lower() or "drop" in sql.lower():
        return [TextContent(type="text", text="Error: 权限不足，MCP 接口仅允许 SELECT 查询。")]

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()
        
        if not rows:
            return [TextContent(type="text", text="查询结果为空")]
            
        # 获取列名
        col_names = [description[0] for description in cursor.description]
        res_str = f"字段: {', '.join(col_names)}\n"
        for row in rows:
            res_str += str(tuple(row)) + "\n"
            
        conn.close()
        return [TextContent(type="text", text=res_str.strip())]
    except Exception as e:
        return [TextContent(type="text", text=f"SQL 执行报错: {str(e)}")]

async def main():
    print("Starting EduAgent MCP Server (Stdio)...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
