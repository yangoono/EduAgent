from app.agents.informer import run_informer, format_subview_as_markdown

def run_data_agent(user_query, current_role, current_sno):
    """
    DataWorker: 专门负责基础数据查询（数据库抽取）的专业 Worker。
    """
    informer_res = run_informer(user_query, current_sno=current_sno, current_role=current_role)
    if informer_res.get("status") == "success":
        formatted = format_subview_as_markdown(informer_res)
        return formatted
    else:
        return f"查询失败: {informer_res.get('message')}"
