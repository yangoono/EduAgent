import sys
import io
import traceback
import contextlib

def run_python_code(code_str):
    """
    执行 Planner 生成的 Python 代码，并捕获输出和错误。
    由于这是演示项目，使用 exec，但在实际生产中需要更严格的沙盒。
    """
    output_buffer = io.StringIO()
    
    # 提取代码内容
    if "```python" in code_str:
        parts = code_str.split("```python")
        if len(parts) > 1:
            code_str = parts[1].split("```")[0].strip()
    elif "```" in code_str:
        parts = code_str.split("```")
        if len(parts) > 1:
            code_str = parts[1].strip()
            
    # 设置运行的全局环境
    exec_globals = {
        '__builtins__': __builtins__,
    }
    
    # 尝试预导入常用库，或者让模型自己 import
    try:
        import pandas as pd
        exec_globals['pd'] = pd
    except ImportError:
        pass
        
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        # 设置无头模式，避免弹出窗口
        matplotlib.use('Agg')
        # 设置支持中文的字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        exec_globals['plt'] = plt
    except ImportError:
        pass

    try:
        with contextlib.redirect_stdout(output_buffer):
            with contextlib.redirect_stderr(output_buffer):
                exec(code_str, exec_globals)
        output = output_buffer.getvalue()
        return {
            "status": "success",
            "output": output if output else "执行成功，无输出。"
        }
    except Exception as e:
        error_msg = traceback.format_exc()
        return {
            "status": "error",
            "output": output_buffer.getvalue(),
            "error": error_msg
        }
