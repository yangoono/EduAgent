import ollama
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def call_llm(messages, system_prompt=None):
    """
    本地 Ollama 模型 (MiniCPM-V 4.6)
    适用场景：最终答案汇总、私有数据处理（敏感数据不出本机）
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


def call_deepseek(messages, system_prompt=None, max_retries=3):
    """
    DeepSeek API（云端）
    适用场景：Text2SQL 生成（仅发送 Schema，不包含敏感数据）
    """
    import time
    msgs = []
    if system_prompt:
        msgs.append({"role": "system", "content": system_prompt})
    for m in messages:
        msgs.append({"role": m["role"], "content": m["content"]})

    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return "[DeepSeek] 未找到 DEEPSEEK_API_KEY，请检查 .env 文件。"

    for attempt in range(max_retries):
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
                    "temperature": 0.1
                },
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                return "[DeepSeek] 请求超时，请检查网络连接。"
            time.sleep(2)
        except requests.exceptions.HTTPError as e:
            if attempt == max_retries - 1:
                return f"[DeepSeek] HTTP 错误: {e.response.status_code} - {e.response.text}"
            time.sleep(2)
        except Exception as e:
            if attempt == max_retries - 1:
                return f"[DeepSeek] 调用失败: {str(e)}"
            time.sleep(2)
