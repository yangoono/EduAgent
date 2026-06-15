from app.rag.pipeline import query_rag
from app import app

def run_retriever(query_text):
    """
    核心 Retriever 模块：
    负责针对学生手册、奖学金条例、毕业政策等进行非结构化 RAG 检索。
    """
    with app.app_context():
        ans, docs = query_rag(query_text)
        if not docs:
            return "Retriever 提示：知识库中没有找到相关规定或政策内容。"
        
        # 整理检索结果，形成子视图 (Subview) 给 Planner 看
        res_str = "Retriever 检索到的相关政策/规定如下：\n"
        for idx, d in enumerate(docs):
            res_str += f"{idx+1}. 【{d['title']}】: {d['content']}\n"
            
        return res_str.strip()
