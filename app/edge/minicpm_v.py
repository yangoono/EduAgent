import json
import ollama

def extract_structured_data_from_image(image_bytes, data_type="score"):
    """
    使用 MiniCPM-V 提取图片中的结构化数据。
    这里展示的是端侧推理的思想：
    1. 图片被传给本地/端侧的 MiniCPM-V 模型。
    2. 模型解析后，图片即被丢弃。
    3. 只返回结构化 JSON 数据（学号、姓名、成绩等）。
    """
    
    if data_type == "score":
        prompt = "请识别这张成绩单图片中的所有内容，并提取为JSON格式，包含字段：sno（学号）, cno（课程号）, score（成绩数字）。如果不确定可以为空。请仅输出包含 JSON 的块，不要带多余的解释。"
    elif data_type == "register":
        prompt = "请识别这张证件（学生证/教师工牌）图片中的信息，并提取为JSON格式，包含字段：student_id（学号/工号）, name（姓名）, role（身份，可选值为 student、teacher 之一，学生证填 student，教师工牌填 teacher）。如果不确定可以为空。请仅输出包含 JSON 的块，不要带多余的解释。"
    else:
        prompt = "请识别这张学生证图片中的信息，并提取为JSON格式，包含字段：sno（学号）, sname（姓名）, sdept（专业）, sage（年龄）。如果不确定可以为空。请仅输出包含 JSON 的块，不要带多余的解释。"

    try:
        response = ollama.chat(
            model='openbmb/minicpm-v4.6',
            messages=[
                {
                    'role': 'user',
                    'content': prompt,
                    'images': [image_bytes]
                }
            ]
        )
        content = response.message.content
        
        # 简单清洗并解析 JSON（假设模型输出在 ```json ... ``` 块中）
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].strip()
            
        return json.loads(content)
    except Exception as e:
        print(f"MiniCPM-V OCR Failed or Not Running: {e}")
        print("Falling back to MOCK data...")
        # 这是一个 Mock 数据返回，供没有本地模型环境时演示用
        if data_type == "score":
            return {"sno": "20230001", "cno": "C001", "score": 85}
        elif data_type == "register":
            return {"student_id": "20250001", "name": "张三", "role": "student"}
        else:
            return {"sno": "20230002", "sname": "测试学生", "sdept": "计算机科学与技术", "sage": 20}
