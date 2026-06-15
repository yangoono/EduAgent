# 智能教务多智能体助手 (EduAgent)

这是一个集成大语言模型 (LLM) 和检索增强生成 (RAG) 技术的智能教务问答与分析系统。该系统针对桂林电子科技大学 (GUET) 的培养方案进行了定制，集成了成绩分析、智能查库和对话辅导功能。

## 🌟 核心特性

- **多角色智能体 (Multi-Agent System)**: 包含管理员(Admin)、教师(Teacher)、学生(Student)专属 Agent，基于角色的权限隔离，防止数据越权访问。
- **自然语言查库 (Text2SQL)**: 用户可以用大白话提问（如“帮我查一下我挂了几科”），系统内置的 Informer 会自动翻译为准确的 SQL 进行查询。
- **自我纠错机制 (Self-Correction)**: Informer 在底层执行 SQL 如果发生报错，会自动捕获错误并让大模型进行自我修复和重新执行。
- **智能数据分析与制图 (Sandbox)**: 能够根据查询到的教务数据动态编写 Python 代码，生成 ECharts 雷达图、分布图等进行深度分析。
- **文档知识检索 (RAG)**: 可上传并检索学校的培养方案、教务规章制度（支持 PDF 解析）。

## 📁 目录结构说明

- `/app/agents/`: AI 核心大脑，包含 Planner, Informer, Retriever 及各角色入口。
- `/app/edge/`: 端侧 AI（MiniCPM-V 等）的图片 OCR 解析与信息提取。
- `/database/`: 数据库初始化和数据模拟脚本（使用 Faker 模拟）。
- `/docs/`: 参考文献与学校教务制度归档。
- `/static/` & `/app/templates/`: Flask 前端页面和资源（含 ECharts 图表渲染逻辑）。
- `.env`: **[请勿上传]** 存放系统环境变量（如 `DEEPSEEK_API_KEY`, `SECRET_KEY` 等）。

## 🚀 快速开始

### 1. 环境准备
```bash
pip install -r requirements.txt
```

### 2. 配置环境变量
在项目根目录创建 `.env` 文件并填入：
```env
DEEPSEEK_API_KEY=your_api_key_here
SECRET_KEY=your_flask_secret_key
DATABASE_URL=sqlite:///teachsys.db
```

### 3. 生成测试数据
该脚本会自动基于桂电培养方案生成 1000 名学生及 1万多条成绩记录：
```bash
python database/data_init.py
```

### 4. 运行系统
```bash
python run.py
```
然后访问 `http://127.0.0.1:5000` 即可登录体验。
