from app.agents.planner import run_planner

def get_admin_response(user_message, history=None):
    """
    管理员 Agent：接入 Planner-Informer-Retriever 三层架构。
    """
    planner_result = run_planner(user_message, current_role='admin')
    
    reply = planner_result["answer"]
        
    return reply, planner_result["thinking_steps"], planner_result.get("echarts_option")
