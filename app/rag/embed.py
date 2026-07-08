import numpy as np

_model = None

def _get_model():
    """懒加载 BGE-M3 模型（首次调用时从 HuggingFace 下载，约 500MB，之后缓存本地）"""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            print("[Embed] 正在加载本地 BGE-M3 Embedding 模型...")
            _model = SentenceTransformer('BAAI/bge-m3')
            print("[Embed] BGE-M3 模型加载完成。")
        except ImportError:
            print("[Embed] 错误：未安装 sentence-transformers，请执行 pip install sentence-transformers")
            return None
        except Exception as e:
            print(f"[Embed] 模型加载失败: {e}")
            return None
    return _model

def get_embedding(text):
    """
    使用本地 BGE-M3 模型生成文本向量（完全离线，隐私安全）
    输出维度：1024
    """
    model = _get_model()
    if model is None:
        # 兜底：返回随机向量，防止系统崩溃
        print("[Embed] 警告：使用随机向量兜底，RAG 检索将不准确！")
        return np.random.rand(1024).tolist()

    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()

def cosine_similarity(v1, v2):
    v1, v2 = np.array(v1), np.array(v2)
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    if norm_v1 == 0 or norm_v2 == 0:
        return 0
    return dot_product / (norm_v1 * norm_v2)
