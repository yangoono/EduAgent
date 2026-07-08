from app.agents.retriever import run_retriever, format_retriever_as_markdown

def run_policy_agent(user_query):
    """
    PolicyWorker: 专门负责规章制度检索的专业 Worker。
    """
    retriever_res = run_retriever(user_query)
    formatted = format_retriever_as_markdown(retriever_res)
    return formatted
