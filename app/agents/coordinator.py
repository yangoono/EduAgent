from app.agents.llm_utils import call_deepseek
from app.agents.sheet_agent import run_sheet_agent
from app.agents.policy_agent import run_policy_agent
from app.agents.data_agent import run_data_agent
from app.agents.memory_manager import EduMemoryManager

_memory = EduMemoryManager()

def run_coordinator(user_query, current_role='student', current_sno=None, step_callback=None):
    """
    Top-level Coordinator Agent: 负责意图识别和任务分发。
    """
    thinking_steps = []
    
    def log_step(msg, step_type="thought"):
        if step_callback:
            step_callback(msg)
        print(f"[Coordinator] {msg}")
        thinking_steps.append({"type": step_type, "content": msg})

    log_step(f"[Coordinator] 收到查询: '{user_query}'。开始拆解任务...", "thought")

    # 检索该用户的历史记忆上下文
    user_id = str(current_sno) if current_sno else "anonymous"
    memory_context = _memory.get_context(user_id=user_id, query=user_query)
    
    intent_prompt = f"""
    你是系统最顶层的大脑(Coordinator)。当前交互的用户角色是: {current_role} (学号/工号: {current_sno})
    用户的查询是："{user_query}"

    [该用户历史偏好与上下文]
    {memory_context if memory_context else '暂无历史记忆。'}
    
    【极其重要的权限规则】：
    - 如果当前角色是 student，他绝不允许查询其他特定同学的成绩明细或画像。
    - 如果识别到越权，直接回复 "REJECT: 权限不足，只能查询本人数据或本班宏观分布"。
    
    你有三个专业 Worker 团队可以调度：
    1. SheetAgent: 负责复杂的数据统计、数据分析、计算和生成可视化图表。
    2. PolicyWorker: 负责检索非结构化的规章制度、教学手册等文本库。
    3. DataWorker: 负责纯结构化的教务数据库查询（仅仅是查信息，不涉及计算或画图）。
    
    请判断应该调用哪个或哪些 Worker 团队？你可以同时调用多个。
    请返回需要调用的 Worker 名称列表，以逗号分隔，例如 "SheetAgent, PolicyWorker" 或 "DataWorker"。
    """
    
    intent = call_deepseek([{"role": "user", "content": intent_prompt}]).strip()
    if intent.startswith("REJECT"):
        log_step(f"[Coordinator] 权限拦截: {intent[7:]}", "observation")
        return {
            "answer": f"抱歉，出于隐私和权限控制，您当前作为学生，{intent[7:]}。",
            "echarts_option": None,
            "context": "权限校验未通过。",
            "sandbox_output": "",
            "thinking_steps": thinking_steps
        }
        
    log_step(f"[Coordinator] 任务拆解完毕，派发任务: {intent}", "observation")

    task_notifications = []
    echarts_option = None
    import concurrent.futures
    import threading

    log_lock = threading.Lock()

    def safe_log(msg, step_type="action"):
        with log_lock:
            log_step(msg, step_type)

    def run_sheet(q, r, s):
        safe_log("[Coordinator] 并发启动 SheetAgent...", "action")
        return "SheetAgent", run_sheet_agent(q, r, s, safe_log)

    def run_policy(q):
        safe_log("[Coordinator] 并发启动 PolicyWorker...", "action")
        return "PolicyWorker", run_policy_agent(q)

    def run_data(q, r, s):
        safe_log("[Coordinator] 并发启动 DataWorker...", "action")
        return "DataWorker", run_data_agent(q, r, s)

    # 构建并发任务列表
    worker_futures = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        if "SheetAgent" in intent:
            worker_futures[executor.submit(run_sheet, user_query, current_role, current_sno)] = "SheetAgent"
        if "PolicyWorker" in intent:
            worker_futures[executor.submit(run_policy, user_query)] = "PolicyWorker"
        if "DataWorker" in intent:
            worker_futures[executor.submit(run_data, user_query, current_role, current_sno)] = "DataWorker"

        # 收集并发结果
        results = {}
        for future in concurrent.futures.as_completed(worker_futures):
            try:
                name, res = future.result()
                results[name] = res
            except Exception as e:
                name = worker_futures[future]
                results[name] = {"summary": f"Worker 执行失败: {e}", "echarts_option": None}

    # 汇总 task-notification
    for name, res in results.items():
        if name == "SheetAgent":
            summary = res.get("summary", "") if isinstance(res, dict) else str(res)
            task_notifications.append(
                f"<task-notification>\n<task-id>SheetAgent</task-id>\n<status>completed</status>\n<result>\n{summary}\n</result>\n</task-notification>"
            )
            if isinstance(res, dict) and res.get("echarts_option"):
                echarts_option = res["echarts_option"]
        else:
            content = res if isinstance(res, str) else str(res)
            task_notifications.append(
                f"<task-notification>\n<task-id>{name}</task-id>\n<status>completed</status>\n<result>\n{content}\n</result>\n</task-notification>"
            )

    log_step("[Coordinator] 所有 Worker 并发执行完毕，正在汇总回答...", "thought")

    
    notifications_str = "\n".join(task_notifications)
    
    final_prompt = f"""
    你是顶层 Coordinator。请根据下属各专业 Worker 团队异步返回的 <task-notification> 结果，为用户生成最终答复。
    
    用户问题: {user_query}
    
    Worker 团队返回的通知记录:
    {notifications_str}
    
    请组织语言给出一个专业、准确的最终答复。如果数据量较大，可用 Markdown 格式排版。
    """
    
    final_answer = call_deepseek([{"role": "user", "content": final_prompt}])

    # 将本轮对话摘要存入用户长效记忆
    _memory.add_memory(
        user_id=user_id,
        text=f"用户询问: {user_query}\n系统回答: {final_answer[:300]}"
    )

    log_step("[Coordinator] 任务完成。", "observation")

    
    return {
        "answer": final_answer,
        "echarts_option": echarts_option,
        "context": notifications_str,
        "sandbox_output": "",
        "thinking_steps": thinking_steps
    }
