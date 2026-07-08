import json
import numpy as np
import faiss
import fitz # PyMuPDF
from app.rag.embed import get_embedding
from app.models import KnowledgeDoc
from app import db
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Global FAISS index and doc mapping
_index = None
_doc_mapping = {}

def get_faiss_index():
    global _index, _doc_mapping
    if _index is None:
        docs = KnowledgeDoc.query.all()
        if not docs:
            return None, None
        
        # Find first valid embedding
        valid_doc = next((d for d in docs if d.embedding), None)
        if not valid_doc:
            return None, None
            
        emb_dim = len(valid_doc.embedding)
        _index = faiss.IndexFlatL2(emb_dim)
        
        vectors = []
        for i, doc in enumerate(docs):
            if doc.embedding:
                vectors.append(doc.embedding)
                _doc_mapping[i] = doc
                
        if vectors:
            _index.add(np.array(vectors, dtype=np.float32))
            
    return _index, _doc_mapping

def rebuild_index():
    global _index, _doc_mapping
    _index = None
    _doc_mapping = {}

def add_document(title, content):
    """
    添加文档并分块存入数据库
    """
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_text(content)
    
    docs_added = []
    for i, chunk in enumerate(chunks):
        chunk_title = f"{title} - Part {i+1}"
        emb = get_embedding(chunk)
        doc = KnowledgeDoc(title=chunk_title, content=chunk, embedding=emb)
        db.session.add(doc)
        docs_added.append(doc)
        
    db.session.commit()
    rebuild_index() # force rebuild
    return docs_added

def process_pdf(pdf_path, title_prefix="PDF"):
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
        return add_document(title_prefix, text)
    except Exception as e:
        print(f"Error parsing PDF: {e}")
        return []

def query_rag(question):
    q_emb = get_embedding(question)
    q_emb_np = np.array([q_emb], dtype=np.float32)
    
    index, mapping = get_faiss_index()
    if index is None or index.ntotal == 0:
        return "暂无相关校园文档知识。", []
        
    k = 3
    distances, indices = index.search(q_emb_np, k)
    
    top_docs = []
    for idx in indices[0]:
        if idx != -1 and idx in mapping:
            top_docs.append(mapping[idx])
            
    if not top_docs:
        context = "暂无相关校园文档知识。"
    else:
        context = "\n\n".join([f"【{d.title}】: {d.content}" for d in top_docs])
        
    prompt = f"""
    你是一个校园智能助理。请根据以下参考资料回答学生的问题。如果参考资料中没有相关信息，请回答“根据现有资料无法得出确切结论”，不要编造。
    
    参考资料：
    {context}
    
    学生问题：
    {question}
    """
    
    from app.agents.llm_utils import call_llm
    messages = [{"role": "user", "content": prompt}]
    
    try:
        answer = call_llm(messages)
        return answer, [d.to_dict() for d in top_docs]
    except Exception as e:
        return f"回答出错: {e}", []
