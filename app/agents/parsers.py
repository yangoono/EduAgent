import re
from typing import Tuple, Optional

class FormatMismatchError(Exception):
    """ReAct 格式解析异常"""
    pass

def parse_react_response(response: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    解析 ReAct 响应
    返回格式: (thought, action, action_input, final_answer)
    其中如果解析到 final_answer，则前三项通常为 None。
    如果格式完全不匹配，抛出 FormatMismatchError
    """
    
    # 尝试提取 Final Answer
    final_answer_match = re.search(r"Final Answer:\s*(.*)", response, re.IGNORECASE | re.DOTALL)
    if final_answer_match:
        return None, None, None, final_answer_match.group(1).strip()
        
    # 尝试提取 Thought
    thought_match = re.search(r"Thought:\s*(.+?)(?:\nAction:|$)", response, re.DOTALL)
    thought = thought_match.group(1).strip() if thought_match else ""
    
    # 尝试提取 Action 和 Action Input
    # 支持 "Action: call_informer" 和 "Action: call_informer(..." 两种常见变体
    action_match = re.search(r"Action:\s*([a-zA-Z0-9_]+)", response)
    
    # Action Input 支持同行或下一行
    action_input_match = re.search(r"Action Input:\s*(.+?)(?:\n|$)", response, re.DOTALL)
    
    action = None
    action_input = ""
    
    if action_match:
        action = action_match.group(1).strip()
        if action_input_match:
            action_input = action_input_match.group(1).strip().strip("\"'")
        else:
            # 兜底：尝试从 Action 那一行提取参数
            same_line = re.search(r"Action:\s*[a-zA-Z0-9_]+[：:（(](.+?)(?:[)）]|$)", response)
            if same_line:
                action_input = same_line.group(1).strip()

    # 如果既没有找到 Final Answer，也没有找到合法的 Action，说明响应格式不符合规范
    if not final_answer_match and not action:
        raise FormatMismatchError("无法解析 Action 或 Final Answer，请严格按照格式要求输出！")
        
    return thought, action, action_input, None
