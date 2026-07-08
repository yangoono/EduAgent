from app.agents.llm_utils import call_llm

def calculate_risk(scores_data):
    """
    计算学业评估与预警。
    红色预警：挂科 >= 2门
    黄色预警：GPA < 2.5
    蓝色提醒：毕业学分完成率不足 (简单模拟: 总学分<80 且 挂科=1 或 GPA<3.0)
    
    参数:
        scores_data: [{'cname': 'xx', 'score': 80, 'ccredit': 2}, ...]
    返回:
        risk_level: '红色预警', '黄色预警', '蓝色提醒', '正常'
        explanation: Agent生成的解释文本
    """
    if not scores_data:
        return '正常', '暂无有效成绩记录。'
    
    fail_count = 0
    total_score_points = 0
    total_credits = 0
    
    reasons = []
    
    for s in scores_data:
        if s.get('score') is None:
            continue
            
        credit = s.get('ccredit', 1)
        score = s['score']
        total_credits += credit
        
        # Calculate GPA points roughly
        if score >= 90: gp = 4.0
        elif score >= 85: gp = 3.7
        elif score >= 82: gp = 3.3
        elif score >= 78: gp = 3.0
        elif score >= 75: gp = 2.7
        elif score >= 72: gp = 2.3
        elif score >= 68: gp = 2.0
        elif score >= 64: gp = 1.5
        elif score >= 60: gp = 1.0
        else:
            gp = 0.0
            fail_count += 1
            reasons.append(f"{s.get('cname', '未知课程')}未通过")
            
        total_score_points += gp * credit
        
    if total_credits == 0:
        return '正常', '暂无有效学分记录。'
        
    gpa = total_score_points / total_credits
    
    risk_level = '正常'
    if fail_count >= 2:
        risk_level = '红色预警'
        reasons.append(f"挂科门数达到 {fail_count} 门")
    elif gpa < 2.5:
        risk_level = '黄色预警'
        reasons.append(f"当前GPA为 {gpa:.2f}，低于2.5")
    elif total_credits < 160 and gpa < 3.0: # Mock logic for completion rate
        risk_level = '蓝色提醒'
        reasons.append(f"毕业学分进度可能不足 (当前已修 {total_credits} 学分)")
        
    if risk_level == '正常':
        reasons.append(f"当前GPA为 {gpa:.2f}，学业状况良好")
        
    # Build prompt for LLM explanation
    reason_text = "；\n".join(reasons)
    prompt = f"""
请扮演学业评估系统，根据以下状态为学生生成一段评估与预警解释。
输出格式要求：
当前状态：[预警级别]
原因：
[原因列表，每点一行]
(你可以适当增加一些导师般的建议，字数在100字左右)

输入状态：
级别：{risk_level}
具体原因：
{reason_text}
"""
    
    try:
        explanation = call_llm([{"role": "user", "content": prompt}], "你是一个专业的大学教务智能助手。")
    except Exception as e:
        # Fallback if LLM fails
        explanation = f"当前状态：\n{risk_level}\n\n原因：\n{reason_text}"
        
    return risk_level, explanation
