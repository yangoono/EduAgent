from app.agents.planner import run_planner

def get_teacher_response(user_message, history=None):
    """
    教师 Agent：接入 Planner-Informer-Retriever 三层架构。
    """
    planner_result = run_planner(user_message, current_role='teacher')
    
    reply = planner_result["answer"]
        
    return reply, planner_result["thinking_steps"], planner_result.get("echarts_option")
