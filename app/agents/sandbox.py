import os
import sys
import json
import tempfile
import subprocess


def run_python_code(code_str: str) -> dict:
    """
    Execute LLM-generated Python code in an isolated subprocess with a 15-second timeout.
    Using subprocess instead of exec() prevents malicious code from accessing the host process.
    """
    # Strip markdown code fences if present
    if "```python" in code_str:
        parts = code_str.split("```python")
        if len(parts) > 1:
            code_str = parts[1].split("```")[0].strip()
    elif "```" in code_str:
        parts = code_str.split("```")
        if len(parts) > 1:
            code_str = parts[1].strip()

    # Prepend common imports so generated code doesn't need to repeat them
    preamble = "import pandas as pd\nimport json\n"
    full_code = preamble + code_str

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, encoding='utf-8'
        ) as f:
            f.write(full_code)
            tmp_path = f.name

        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=15,
            encoding='utf-8',
            errors='replace'
        )

        output = result.stdout
        stderr = result.stderr

        if result.returncode != 0:
            return {
                "status": "error",
                "output": output,
                "error": stderr
            }

        return {
            "status": "success",
            "output": output if output else "执行成功，无标准输出。"
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "output": "",
            "error": "代码执行超时（超过 15 秒），已强制终止。"
        }
    except Exception as e:
        return {
            "status": "error",
            "output": "",
            "error": f"沙盒启动失败: {str(e)}"
        }
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
