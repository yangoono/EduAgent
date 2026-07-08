from app import db
from sqlalchemy import text
from app.agents.llm_utils import call_deepseek
import json

DATABASE_SCHEMA = """
Table: students
Columns: sno (String, primary_key), sname (String), ssex (String), sage (Integer), sdept (String), hometown (String)

Table: courses
Columns: cno (String, primary_key), cname (String), cpno (String, foreign_key to courses.cno), ccredit (Integer), cteacher (String)

Table: score
Columns: sno (String, foreign_key to students.sno), cno (String, foreign_key to courses.cno), score (Integer)

Table: teachers
Columns: tno (String, primary_key), tname (String), tdept (String)
"""

def extract_sql_from_response(response):
    """
    提取大模型返回文本中的 SQL 语句。
    支持提取 ```sql ... ``` 或者纯文本中的 SQL。
    """
    if "```sql" in response:
        parts = response.split("```sql")
        if len(parts) > 1:
            sql = parts[1].split("```")[0].strip()
            return sql
    elif "```" in response:
        parts = response.split("```")
        if len(parts) > 1:
            sql = parts[1].strip()
            return sql
    return response.strip()

def run_informer(user_query, current_sno=None, current_role='student'):
    """
    Informer Agent: 将用户的自然语言查询转换为 SQL，执行并返回表格数据。
    这对应 SheetAgent 中的 Informer 模块，负责从海量数据中提取有用的子视图(Subview)。
    """
    system_prompt = f"""
    你是一个负责教务数据库查询的 Informer Agent（SQL 专家）。
    你的任务是将用户问题转换为针对 MySQL 数据库的单个可用 SELECT 查询。
    只返回可执行的 SQL 语句，不要有任何解释或其他文字。
    
    【当前登录用户上下文】
    当前用户角色: {current_role}
    当前用户学号(sno): {current_sno if current_sno else '无'}
    如果用户查询中提到“我”、“我的”并且有具体的学号信息，你必须在 SQL 中加上 `WHERE sno = '{current_sno}'` 的过滤条件！
    千万不要在SQL中使用形如 '你的姓名' 这种无效的占位符！
    
    以下是数据库 Schema：
    {DATABASE_SCHEMA}
    """
    
    messages = [{"role": "user", "content": user_query}]
    
    max_retries = 3
    for attempt in range(max_retries):
        # 使用 DeepSeek 生成 SQL
        llm_sql_response = call_deepseek(messages, system_prompt=system_prompt)
        
        if "[DeepSeek]" in llm_sql_response and ("失败" in llm_sql_response or "错误" in llm_sql_response):
            return {"status": "error", "message": llm_sql_response, "data": []}
            
        sql = extract_sql_from_response(llm_sql_response)
        
        if not sql.lower().startswith("select"):
            return {"status": "error", "message": "生成了非法的查询语句", "sql": sql, "data": []}
        
        # 执行 SQL
        try:
            # 避免大查询，强制限制
            if "limit" not in sql.lower():
                sql += " LIMIT 100"
                
            result = db.session.execute(text(sql))
            keys = result.keys()
            data = [dict(zip(keys, row)) for row in result.fetchall()]
            
            return {
                "status": "success",
                "sql": sql,
                "data": data,
                "columns": list(keys)
            }
        except Exception as e:
            error_msg = str(e)
            if attempt < max_retries - 1:
                # 记录错误，进行自我纠错 (Self-Correction)
                messages.append({"role": "assistant", "content": f"```sql\n{sql}\n```"})
                messages.append({"role": "user", "content": f"执行上述 SQL 失败，数据库返回错误：\n{error_msg}\n请你分析错误原因，修正 SQL 语法并重新输出正确的 SQL 语句。注意只返回可执行的 SQL。"})
            else:
                return {"status": "error", "message": f"执行 SQL 失败(已重试{max_retries}次): {error_msg}", "sql": sql, "data": []}

def format_subview_as_markdown(informer_result):
    """
    将 Informer 的结果格式化为 Markdown 表格，供 Planner 阅读
    """
    if informer_result.get("status") == "error":
        return f"查询失败: {informer_result.get('message')}\nSQL: {informer_result.get('sql', '无')}"
        
    data = informer_result.get("data", [])
    if not data:
        return f"SQL 查询执行成功，但没有找到符合条件的数据。\n执行的 SQL: {informer_result.get('sql')}"
        
    columns = informer_result.get("columns", [])
    
    # 构建表头
    md = "| " + " | ".join(columns) + " |\n"
    md += "|" + "|".join(["---"] * len(columns)) + "|\n"
    
    # 构建数据行
    for row in data:
        row_str = "| " + " | ".join([str(row.get(col, "")) for col in columns]) + " |\n"
        md += row_str
        
    return f"【Informer 提取的数据子视图 Subview】\n执行的 SQL: {informer_result.get('sql')}\n\n" + md
