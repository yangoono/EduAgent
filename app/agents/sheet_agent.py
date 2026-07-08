import json
from app.agents.llm_utils import call_deepseek
from app.agents.informer import run_informer, format_subview_as_markdown
from app.agents.sandbox import run_python_code

def run_sheet_agent(user_query, current_role, current_sno, log_step):
    """
    SheetAgent: The SheetRM planner-informer-retriever triad subsystem.
    Handles data extraction, Python charting, and complex calculations.
    """
    log_step(f"[SheetAgent] 正在调用 Informer 抽取数据子视图...", "action")
    informer_res = run_informer(user_query, current_sno=current_sno, current_role=current_role)
    
    if informer_res.get("status") != "success":
        log_step(f"[SheetAgent] Informer 查询失败：{informer_res.get('message')}", "observation")
        return {"summary": "数据提取失败", "echarts_option": None}
        
    json_data_for_python = informer_res.get("data", [])
    sql_executed = informer_res.get('sql', '')
    data_summary = format_subview_as_markdown(informer_res)
    
    log_step(f"[SheetAgent] Informer 数据抽取完毕，得到 {len(json_data_for_python)} 条数据。", "observation")
    
    if not json_data_for_python:
        return {"summary": "提取的数据为空", "echarts_option": None}

    log_step(f"[SheetAgent] 正在调用 Planner 编写 Python 脚本以进行复杂分析并绘图...", "action")
    
    code_prompt = f"""
    你现在要生成一段 Python 代码来处理数据并回答用户。环境已经内置了 pandas as pd。
    
    输入数据被定义为 python 变量 `data`：
    data = {json.dumps(json_data_for_python[:50], ensure_ascii=False)} # 仅展示前50条
    
    【核心可视化任务 (ECharts)】:
    如果需要画图，请在 Python 代码中构建一个字典变量 `echarts_option`，该字典必须是标准的 ECharts 配置项。
    
    在代码的最后，请使用以下代码输出这个 JSON：
    ```python
    import json
    print("__ECHARTS__" + json.dumps(echarts_option, ensure_ascii=False))
    ```
    
    用户问题：{user_query}
    
    请只返回包裹在 ```python ... ``` 中的代码。不需要任何其他解释文字。
    """
    code_res = call_deepseek([{"role": "user", "content": code_prompt}])
    
    full_code = f"data = {json.dumps(json_data_for_python, ensure_ascii=False)}\nimport pandas as pd\ndf = pd.DataFrame(data)\n" + code_res
    
    sandbox_res = run_python_code(full_code)
    sandbox_output = sandbox_res.get("output", "")
    
    echarts_option = None
    if "__ECHARTS__" in sandbox_output:
        try:
            json_str = sandbox_output.split("__ECHARTS__")[1].strip()
            echarts_option = json.loads(json_str)
            sandbox_output = sandbox_output.split("__ECHARTS__")[0].strip()
            log_step(f"[SheetAgent] Planner 成功绘制图表。", "observation")
        except Exception as e:
            log_step(f"[SheetAgent] 图表 JSON 解析失败: {e}", "observation")
    else:
        log_step(f"[SheetAgent] Planner 执行完毕。", "observation")
        
    summary = f"提取数据并执行了 Python 脚本分析。\n\n**抽取的数据视图**:\n{data_summary}\n\n**Python 沙盒输出**:\n{sandbox_output}"
    return {"summary": summary, "echarts_option": echarts_option}
