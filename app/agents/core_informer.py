import json
import re
from sqlalchemy import text
from app import app, db
from app.agents.llm_utils import call_deepseek

# Informer 能够看到的数据库 Schema
DATABASE_SCHEMA = """
表结构说明如下：
1. students (学生表):
   - sno: 学号 (VARCHAR)
   - sname: 姓名 (VARCHAR)
   - ssex: 性别 (VARCHAR)
   - sage: 年龄 (INTEGER)
   - sdept: 所在院系/专业 (VARCHAR)
   - hometown: 籍贯 (VARCHAR)

2. courses (课程表):
   - cno: 课程号 (VARCHAR)
   - cname: 课程名 (VARCHAR)
   - cpno: 先修课程号 (VARCHAR)
   - ccredit: 学分 (INTEGER)
   - cteacher: 任课教师 (VARCHAR)

3. score (成绩表):
   - sno: 学号 (VARCHAR, 关联 students.sno)
   - cno: 课程号 (VARCHAR, 关联 courses.cno)
   - score: 分数 (INTEGER)
"""

INFORMER_PROMPT = """你是一个专业的数据库查询分析师（Informer Agent）。
你的任务是根据用户的自然语言需求，结合给定的数据库 Schema，生成准确无误的 SQL 查询语句（仅支持 SQLite 语法）。

{schema}

要求：
1. 你的输出必须且只能包含合法的 SQL 语句，不要有任何其他解释文字。
2. 使用 ```sql ... ``` 代码块包裹 SQL 语句。
3. 请考虑多表 JOIN 的情况，例如查询学生某门课成绩需要 JOIN students 和 score 表。

示例：
用户: 查询学号20230001的学生的及格总学分
输出:
```sql
SELECT SUM(c.ccredit) 
FROM score s 
JOIN courses c ON s.cno = c.cno 
WHERE s.sno = '20230001' AND s.score >= 60;
```
"""

def extract_sql(llm_response):
    """从 LLM 的回复中提取 SQL 语句"""
    match = re.search(r"```sql(.*?)```", llm_response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return llm_response.strip()

def run_informer_nl2sql(query_text):
    """
    核心 Informer 模块：
    1. 接收自然语言 query_text
    2. 翻译为 SQL
    3. 执行 SQL 并返回精确结果 (Subview)
    """
    prompt = f"用户查询需求: {query_text}"
    messages = [
        {"role": "user", "content": prompt}
    ]
    
    # 1. 用 DeepSeek API 生成 SQL（仅发送 Schema + 问题，无真实学生数据）
    llm_response = call_deepseek(messages, system_prompt=INFORMER_PROMPT.format(schema=DATABASE_SCHEMA))
    sql_query = extract_sql(llm_response)
    print(f"[Informer] DeepSeek Generated SQL:\n{sql_query}\n")
    
    # 2. 执行 SQL
    try:
        with app.app_context():
            result = db.session.execute(text(sql_query))
            rows = result.fetchall()
            
            # 将结果转为字符串返回
            if not rows:
                return f"Informer查询结果为空。执行的SQL: {sql_query}"
            
            # 获取列名
            keys = result.keys()
            res_str = f"Informer查询结果 (字段: {', '.join(keys)}):\n"
            for row in rows:
                res_str += str(tuple(row)) + "\n"
                
            return res_str.strip()
            
    except Exception as e:
        return f"Informer 执行 SQL 报错: {str(e)}\n生成的 SQL: {sql_query}"
