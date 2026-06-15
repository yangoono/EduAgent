import json
import os
from app.agents.llm_utils import call_deepseek
from app.agents.informer import run_informer, format_subview_as_markdown
from app.agents.retriever import run_retriever, format_retriever_as_markdown
from app.agents.sandbox import run_python_code

def run_planner(user_query, current_role='student', current_sno=None, step_callback=None):
    """
    Planner Agent: 系统的中枢大脑，受 SheetAgent 启发。
    调度 Informer 和 Retriever，获取上下文后，如需复杂计算或画图，
    则生成 Python 代码并通过 Sandbox 运行。最终合成结果返回。
    """
    
    thinking_steps = []
    
    def log_step(msg, step_type="thought"):
        if step_callback:
            step_callback(msg)
        print(f"[Planner] {msg}")
        thinking_steps.append({"type": step_type, "content": msg})

    log_step(f"🧠 收到查询: '{user_query}'。正在分析意图并决定需要调用的 Agent...", "thought")
    
    intent_prompt = f"""
    你是一个教务系统的 Planner Agent。当前交互的用户角色是: {current_role} (学号/工号: {current_sno})
    用户的查询是："{user_query}"
    
    【极其重要的权限规则】：
    - 如果当前角色是 student，他**绝不允许**查询其他特定同学（如指定学号/姓名）的成绩明细或画像。
    - 如果当前角色是 student，他只允许查询本人的成绩雷达图、本人的排名、或者全班宏观的成绩分布柱状图。
    - 如果识别到用户越权（比如学生试图查别人的成绩雷达图），请立即回复 "REJECT: 权限不足，只能查询本人数据或本班宏观分布"。
    
    你有两个下属 Agent 可以调用：
    1. Informer: 可以查阅数据库，获取学生、成绩、课程、教师等结构化数据表格。
    2. Retriever: 可以检索规章制度、教学手册等非结构化校园文档。
    
    请判断应该调用哪个 Agent。只能回复 "Informer" 或 "Retriever" 或 "Both" 或 "None"（如果是权限拒绝则回复 REJECT 开头的句子）。
    - 如果涉及统计、成绩、名单、课程安排，回复 "Informer"
    - 如果涉及制度、指南、文档、文本知识，回复 "Retriever"
    - 如果都涉及，回复 "Both"
    """
    
    intent = call_deepseek([{"role": "user", "content": intent_prompt}]).strip()
    
    if intent.startswith("REJECT"):
        log_step(f"🚨 权限拦截: {intent[7:]}", "observation")
        return {
            "answer": f"抱歉，出于隐私和权限隔离控制，您当前作为学生，{intent[7:]}。",
            "chart": "",
            "echarts_option": None,
            "context": "权限校验未通过。",
            "sandbox_output": "",
            "thinking_steps": thinking_steps
        }
        
    log_step(f"🎯 意图识别结果: 需要调用 {intent}", "observation")
    
    context_data = ""
    json_data_for_python = []
    
    # 2. 调度子 Agent
    if "Informer" in intent or "Both" in intent:
        log_step(f"🔍 决定调用 Informer：正在让大语言模型根据问题编写 SQL，从教务数据库中检索数据...", "action")
        informer_res = run_informer(user_query, current_sno=current_sno, current_role=current_role)
        if informer_res.get("status") == "success":
            json_data_for_python = informer_res.get("data", [])
            sql_executed = informer_res.get('sql', '')
            log_step(f"✅ Informer 已成功生成 SQL 并查出 {len(json_data_for_python)} 条数据。\n👉 **执行的 SQL**: \n```sql\n{sql_executed}\n```", "observation")
        else:
            log_step(f"❌ Informer 执行失败：{informer_res.get('message')}", "observation")
        context_data += format_subview_as_markdown(informer_res) + "\n\n"
        
    if "Retriever" in intent or "Both" in intent:
        log_step("📚 调用 Retriever 检索校园文档知识库...", "action")
        retriever_res = run_retriever(user_query)
        context_data += format_retriever_as_markdown(retriever_res) + "\n\n"
        log_step("✅ Retriever 检索完毕。", "observation")
        
    # 3. 决定是否需要数据分析/画图 (Sandbox)
    need_sandbox = False
    sandbox_output = ""
    echarts_option = None
    
    if json_data_for_python:
        log_step("🤔 评估是否需要进行复杂数据分析或绘制图表...", "thought")
        analysis_prompt = f"""
        用户查询: {user_query}
        提取的数据条数: {len(json_data_for_python)}
        
        请判断用户的请求是否需要进行复杂的数据计算（如方差、分布统计）或生成图表（饼图、柱状图等）。
        如果需要，回复 "YES"；如果仅仅是查询基本信息，回复 "NO"。只回复 YES 或 NO。
        """
        ans_need = call_deepseek([{"role": "user", "content": analysis_prompt}]).strip().upper()
        
        if "YES" in ans_need:
            need_sandbox = True
            log_step("💻 决定调用 Sandbox 编写并执行 Python 脚本处理数据...", "action")
            
            # 生成 Python 代码
            
            code_prompt = f"""
            你现在要生成一段 Python 代码来处理数据并回答用户。环境已经内置了 pandas as pd。
            
            输入数据被定义为 python 变量 `data`：
            data = {json.dumps(json_data_for_python[:50], ensure_ascii=False)} # 仅展示前50条
            
            【核心可视化任务 (ECharts)】:
            如果用户要求画图（例如成绩分布、雷达图、关联画像等），**请不要**使用 matplotlib 绘图！
            请你在 Python 代码中构建一个字典变量 `echarts_option`，该字典必须是标准的 ECharts 配置项（包含 xAxis, yAxis, series 等）。
            
            【高级算法提示】:
            - 如果用户要求“课程关联画像”：请使用 `pandas` 的 `.corr()` 计算皮尔逊相关系数(Pearson Correlation)，并生成 ECharts 的热力图(Heatmap)或散点图(Scatter)。
            - 如果用户要求“学业预警趋势/分层”：请统计每个学生的挂科数，将学生分为“安全(0科)、预警(1-2科)、严重(>=3科)”，并生成漏斗图(Funnel)或玫瑰图(Nightingale Rose)。
            
            在代码的最后，请使用以下代码输出这个 JSON：
            ```python
            import json
            print("__ECHARTS__" + json.dumps(echarts_option, ensure_ascii=False))
            ```
            
            用户问题：{user_query}
            
            请只返回包裹在 ```python ... ``` 中的代码。不需要任何其他解释文字。
            """
            code_res = call_deepseek([{"role": "user", "content": code_prompt}])
            
            log_step(f"🚀 让 AI 生成数据分析与图表渲染的 Python 代码并在 Sandbox 中执行...", "action")
            # 注入 data 变量的技巧：将 data 定义拼接到生成的代码前
            full_code = f"data = {json.dumps(json_data_for_python, ensure_ascii=False)}\nimport pandas as pd\ndf = pd.DataFrame(data)\n" + code_res
            
            sandbox_res = run_python_code(full_code)
            sandbox_output = sandbox_res.get("output", "")
            
            # 尝试解析 __ECHARTS__ JSON
            if "__ECHARTS__" in sandbox_output:
                try:
                    json_str = sandbox_output.split("__ECHARTS__")[1].strip()
                    echarts_option = json.loads(json_str)
                    log_step(f"📊 分析完成！成功提取图表 JSON 配置。\n👉 **AI 生成的 Python 代码**: \n```python\n{code_res}\n```", "observation")
                    sandbox_output = sandbox_output.split("__ECHARTS__")[0].strip()
                except Exception as e:
                    log_step(f"❌ 解析图表 JSON 配置失败: {e}", "observation")
            else:
                log_step(f"✅ Sandbox Python 代码执行完毕。\n👉 **AI 生成的 Python 代码**: \n```python\n{code_res}\n```\n输出结果:\n{sandbox_output}", "observation")

    # 4. 汇总生成最终回答
    log_step("✍️ 汇总所有 Agent 的结果，生成最终回复...", "thought")
    final_prompt = f"""
    你是桂林电子科技大学研发的 SheetAgent 多智能体教务助手。
    请根据以下各个子模块收集到的信息，回答用户的问题。
    
    用户问题: {user_query}
    
    【知识与数据上下文】
    {context_data}
    
    【Python Sandbox 分析结果】
    {sandbox_output if sandbox_output else '未使用 Sandbox'}
    
    请组织语言给出一个专业、准确的最终答复。如果是表格数据，可以使用 Markdown 表格。
    """
    
    final_answer = call_deepseek([{"role": "user", "content": final_prompt}])
    
    log_step("🎉 任务完成！", "observation")
    
    return {
        "answer": final_answer,
        "echarts_option": echarts_option,
        "context": context_data,
        "sandbox_output": sandbox_output,
        "thinking_steps": thinking_steps
    }
