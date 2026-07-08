from app.rag.pipeline import query_rag

def run_retriever(user_query):
    """
    Retriever Agent: 使用现有的 RAG 系统从知识库文档中检索相关知识。
    这对应 SheetAgent 中获取相关代码/外部知识的功能，这里适配为校园知识检索。
    """
    answer, docs = query_rag(user_query)
    
    if not docs:
        return {
            "status": "success",
            "answer": answer,
            "has_docs": False,
            "docs": []
        }
        
    return {
        "status": "success",
        "answer": answer,
        "has_docs": True,
        "docs": docs
    }

def format_retriever_as_markdown(retriever_result):
    if not retriever_result.get("has_docs"):
        return f"【Retriever 检索结果】\n{retriever_result.get('answer')}"
        
    md = f"【Retriever 检索结果】\n{retriever_result.get('answer')}\n\n**参考文档**:\n"
    for doc in retriever_result.get("docs", []):
        md += f"- {doc.get('title')}: {doc.get('content')[:100]}...\n"
        
    return md
