import os
import json
import sqlite3
import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# ---------------------------------------------------------------------------
# MCP Server initialisation
# ---------------------------------------------------------------------------
app = Server("EduAgent-MCP-Server")

DB_PATH = os.path.join(os.path.dirname(__file__), "database", "teachsys.db")

# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------
_TOOLS = [
    Tool(
        name="query_edu_database",
        description="执行 SQLite SELECT 语句查询教务系统数据库（包含 students, courses, score, teachers 等表）。仅允许只读查询。",
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
    ),
    Tool(
        name="search_policy_docs",
        description="从教务规章制度知识库（RAG）中检索与问题相关的政策条文、毕业要求、奖学金规则等非结构化文档。",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "自然语言检索问题"
                }
            },
            "required": ["query"]
        }
    ),
    Tool(
        name="run_python_sandbox",
        description="在受控的隔离沙盒中执行一段 Python 代码，支持 pandas 数据处理，并返回标准输出结果。代码执行超时上限为 15 秒。",
        inputSchema={
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "需要执行的 Python 代码字符串"
                }
            },
            "required": ["code"]
        }
    ),
    Tool(
        name="get_student_profile",
        description="查询指定学生的多维学情画像，包括基本信息、总学分、平均绩点（GPA）及各科成绩汇总。",
        inputSchema={
            "type": "object",
            "properties": {
                "sno": {
                    "type": "string",
                    "description": "学生学号"
                }
            },
            "required": ["sno"]
        }
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    return _TOOLS


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:

    if name == "query_edu_database":
        return await _tool_query_database(arguments)

    if name == "search_policy_docs":
        return await _tool_search_policy(arguments)

    if name == "run_python_sandbox":
        return await _tool_run_sandbox(arguments)

    if name == "get_student_profile":
        return await _tool_get_profile(arguments)

    raise ValueError(f"未知工具: {name}")


async def _tool_query_database(arguments: dict) -> list[TextContent]:
    sql = arguments.get("sql", "").strip()
    if not sql:
        return [TextContent(type="text", text="Error: 缺少 sql 参数。")]

    # Whitelist: only SELECT allowed
    lower_sql = sql.lower()
    for forbidden in ("delete", "update", "insert", "drop", "alter", "create", "replace"):
        if forbidden in lower_sql:
            return [TextContent(type="text", text="Error: 权限不足，MCP 接口仅允许 SELECT 查询。")]

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Enforce row limit to prevent runaway queries
        if "limit" not in lower_sql:
            sql += " LIMIT 200"
        cursor.execute(sql)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return [TextContent(type="text", text="查询结果为空。")]

        col_names = [d[0] for d in cursor.description]
        lines = ["字段: " + ", ".join(col_names)]
        for row in rows:
            lines.append(str(tuple(row)))
        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"SQL 执行报错: {str(e)}")]


async def _tool_search_policy(arguments: dict) -> list[TextContent]:
    query = arguments.get("query", "").strip()
    if not query:
        return [TextContent(type="text", text="Error: 缺少 query 参数。")]
    try:
        # Run blocking RAG call in a thread to avoid blocking the event loop
        from app.rag.pipeline import query_rag
        loop = asyncio.get_event_loop()
        answer, docs = await loop.run_in_executor(None, query_rag, query)
        result = f"【检索答案】\n{answer}\n"
        if docs:
            result += "\n【参考文档】\n"
            for doc in docs:
                result += f"- {doc.get('title', '未知')}: {str(doc.get('content', ''))[:120]}...\n"
        return [TextContent(type="text", text=result)]
    except Exception as e:
        return [TextContent(type="text", text=f"知识库检索失败: {str(e)}")]


async def _tool_run_sandbox(arguments: dict) -> list[TextContent]:
    code = arguments.get("code", "").strip()
    if not code:
        return [TextContent(type="text", text="Error: 缺少 code 参数。")]
    try:
        from app.agents.sandbox import run_python_code
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_python_code, code)
        status = result.get("status", "error")
        output = result.get("output", "")
        error = result.get("error", "")
        text = f"状态: {status}\n输出:\n{output}"
        if error:
            text += f"\n错误:\n{error}"
        return [TextContent(type="text", text=text)]
    except Exception as e:
        return [TextContent(type="text", text=f"沙盒调用失败: {str(e)}")]


async def _tool_get_profile(arguments: dict) -> list[TextContent]:
    sno = arguments.get("sno", "").strip()
    if not sno:
        return [TextContent(type="text", text="Error: 缺少 sno 参数。")]
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Basic info
        cursor.execute("SELECT sno, sname, ssex, sage, sdept FROM students WHERE sno = ?", (sno,))
        student = cursor.fetchone()
        if not student:
            conn.close()
            return [TextContent(type="text", text=f"未找到学号为 {sno} 的学生。")]

        # GPA and total credits
        cursor.execute("""
            SELECT COUNT(*) AS course_count,
                   ROUND(AVG(sc.score), 2) AS avg_score,
                   SUM(c.ccredit) AS total_credit
            FROM score sc
            JOIN courses c ON sc.cno = c.cno
            WHERE sc.sno = ?
        """, (sno,))
        stats = cursor.fetchone()

        # Score breakdown
        cursor.execute("""
            SELECT c.cname, c.ccredit, sc.score
            FROM score sc
            JOIN courses c ON sc.cno = c.cno
            WHERE sc.sno = ?
            ORDER BY sc.score DESC
        """, (sno,))
        scores = cursor.fetchall()
        conn.close()

        lines = [
            f"【学生画像】",
            f"学号: {student[0]}  姓名: {student[1]}  性别: {student[2]}  年龄: {student[3]}  院系: {student[4]}",
            f"已修课程数: {stats[0]}  平均分: {stats[1]}  已获学分: {stats[2]}",
            "",
            "课程成绩明细:",
        ]
        for row in scores:
            lines.append(f"  {row[0]} ({row[1]}学分): {row[2]} 分")

        return [TextContent(type="text", text="\n".join(lines))]

    except Exception as e:
        return [TextContent(type="text", text=f"学情画像查询失败: {str(e)}")]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main():
    print("Starting EduAgent MCP Server (Stdio)...")
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
