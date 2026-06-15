import re
from app.agents.llm_utils import call_deepseek   # Planner 用 DeepSeek 做多步规划
from app.agents.core_informer import run_informer_nl2sql
from app.agents.core_retriever import run_retriever

PLANNER_PROMPT = """你是一个校园智能助手。请严格按照以下步骤回答问题。

【可用工具】
- call_informer：查询数据库中的精确数据（成绩、学分、课程等）
- call_retriever：查询政策文档（毕业要求、奖学金条件等）

【输出格式规则——必须严格遵守】
每次只能做以下两件事之一：

(A) 调用工具：
Thought: （一句话说明为什么要调用这个工具）
Action: call_informer
Action Input: （具体的查询需求，写在这一行）

(B) 给出最终答案：
Final Answer: （你的完整回答，结合工具返回的数据）

【禁止】
- 禁止在一次回复中同时写多个 Action
- 禁止在 Action 后面跟着 "with parameters" 或数字列表
- 禁止省略 "Action Input:" 这一行
- 禁止自己编造数据库中的数据

【正确示例】
用户: 查我的成绩
Thought: 需要查询该学生的成绩记录。
Action: call_informer
Action Input: 查询学号为 {sno} 的所有课程成绩和GPA

【错误示例（禁止这样写）】
Action: 
1. call_retriever...
2. call_informer...
"""

def get_planner_response(user_message, history=None, context_info=None):
    """
    核心 Planner 执行逻辑
    返回值: (final_answer: str, new_history: list, thinking_steps: list)
    """
    messages = history or []
    thinking_steps = []

    info_prompt = f"\n[系统提示：{context_info}]" if context_info else ""
    prompt = f"用户问题: {user_message}{info_prompt}\n\n请严格按照格式回答，每次只做一件事（调用一个工具 或 给出Final Answer）。"

    messages.append({"role": "user", "content": prompt})

    max_steps = 6
    for step in range(max_steps):
        response = call_deepseek(messages, PLANNER_PROMPT)
        print(f"\n=== [Planner Step {step+1}] ===\n{response}\n===========================\n")

        # 更宽容的正则：支持 "Action: call_informer" 和 "Action: call_informer(..." 两种写法
        action_match = re.search(r"Action:\s*(call_informer|call_retriever)", response)
        # Action Input 支持同行或下一行
        action_input_match = re.search(r"Action Input:\s*(.+?)(?:\n|$)", response, re.DOTALL)
        thought_match = re.search(r"Thought:\s*(.+?)(?:\nAction:|$)", response, re.DOTALL)
        final_answer_match = re.search(r"Final Answer:\s*(.*)", response, re.IGNORECASE | re.DOTALL)

        # 提取 Thought
        if thought_match:
            thinking_steps.append({"type": "thought", "content": thought_match.group(1).strip()})

        if action_match:
            action = action_match.group(1).strip()
            action_input = ""
            if action_input_match:
                action_input = action_input_match.group(1).strip().strip("\"'")
            else:
                # 兜底：尝试从 Action 那一行提取参数（针对模型把参数写在同一行的情况）
                same_line = re.search(r"Action:\s*(?:call_informer|call_retriever)[：:（(](.+?)(?:[)）]|$)", response)
                if same_line:
                    action_input = same_line.group(1).strip()

            thinking_steps.append({"type": "action", "content": f"{action}({action_input})"})
            print(f"[Planner] 工具: {action} | 参数: {action_input}")

            observation = f"未知工具: {action}"
            if action == "call_informer":
                observation = run_informer_nl2sql(action_input)
            elif action == "call_retriever":
                observation = run_retriever(action_input)

            thinking_steps.append({"type": "observation", "content": observation})
            print(f"[Planner Observation]\n{observation}\n")

            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "user", "content": f"Observation: {observation}\n\n工具返回了以上数据。如果数据足够，请直接输出 Final Answer 给用户；如果还需要更多数据，请继续调用工具。"})
            continue

        if final_answer_match:
            return final_answer_match.group(1).strip(), messages, thinking_steps

        # 格式错误兜底
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": "格式错误！请只输出以下格式之一：\n1. Thought/Action/Action Input（调用工具）\n2. Final Answer:（直接回答）"})

    return "思考步数超出上限，请重新提问。", messages, thinking_steps
