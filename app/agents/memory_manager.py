import os
try:
    from mem0 import Memory
except ImportError:
    Memory = None

class EduMemoryManager:
    """
    User context manager using mem0.
    Handles storage and retrieval of persistent user profiles and preferences.
    """
    def __init__(self):
        # 初始化 Mem0 实例，默认会使用本地 SQLite 或 Chroma 存储向量记忆
        if Memory is not None:
            self.m = Memory()
        else:
            self.m = None

    def add_memory(self, user_id: str, text: str):
        """
        Store conversation history to update user profile.
        """
        if self.m is None:
            return
            
        # Note: mem0 relies on environment variables for LLM configuration.
        try:
            self.m.add(text, user_id=user_id)
        except Exception as e:
            print(f"[MemoryManager] 添加记忆失败: {e}")

    def get_context(self, user_id: str, query: str) -> str:
        """
        Retrieve context relevant to the current query.
        """
        if self.m is None:
            return ""
        try:
            related_memories = self.m.search(query, user_id=user_id)
            if related_memories:
                context_lines = [mem['text'] for mem in related_memories if 'text' in mem]
                if context_lines:
                    return "[User Profile Context]\n" + "\n".join(context_lines)
            return ""
        except Exception as e:
            print(f"[MemoryManager] 检索记忆失败: {e}")
            return ""
