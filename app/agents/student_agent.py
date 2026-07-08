from app.agents.planner import run_planner

def get_student_response(user_message, history=None, current_sno=None):
    """
    学生 Agent：接入 Planner-Informer-Retriever 三层架构。
    """
    planner_result = run_planner(user_message, current_role='student', current_sno=current_sno)
    
    reply = planner_result["answer"]
    
    return reply, history, planner_result["thinking_steps"], planner_result.get("echarts_option")
