from app.agents.coordinator import run_coordinator

def run_planner(user_query, current_role='student', current_sno=None, step_callback=None):
    """
    为了向前兼容原有的 run_planner 接口，
    将其请求直接转发给新架构的顶层 Coordinator。
    """
    return run_coordinator(user_query, current_role, current_sno, step_callback)
