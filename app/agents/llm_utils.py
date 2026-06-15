import ollama
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def call_llm(messages, system_prompt=None):
    """
    本地 Ollama 模型 (MiniCPM-V 4.6)
    用于：最终答案汇总、对话回复（真实学生数据在此处理，不出本机）
    """
    msgs = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    for m in messages:
        msgs.append({"role": m["role"], "content": m["content"]})
    try:
        response = ollama.chat(model='openbmb/minicpm-v4.6', messages=msgs)
        return response.message.content
    except Exception as e:
        print(f"[Local LLM] Ollama Error: {e}")
        return "本地 AI 模型异常，请确认 Ollama 已启动并执行: ollama run openbmb/minicpm-v4.6"


def call_deepseek(messages, system_prompt=None):
    """
    DeepSeek API（云端）
    用于：Text2SQL 生成（仅发送 Schema + 自然语言，不含真实学生数据）
    """
    msgs = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    for m in messages:
        msgs.append({"role": m["role"], "content": m["content"]})

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return "[DeepSeek] 未找到 DEEPSEEK_API_KEY，请检查 .env 文件。"

    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": msgs,
                "temperature": 0.1   # SQL 生成要保持稳定，温度调低
            },
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        return "[DeepSeek] 请求超时，请检查网络连接。"
    except requests.exceptions.HTTPError as e:
        return f"[DeepSeek] HTTP 错误: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"[DeepSeek] 调用失败: {str(e)}"
