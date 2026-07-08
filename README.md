# EduAgent (智能教务多角色协同智能体系统)

基于大语言模型 (LLM) 和前沿的**主从式分层多智能体（Coordinator-Worker）架构**构建的校园教务问答与分析系统。针对高校场景开发，能够高效处理规章检索、成绩查询、复杂学分测算及画像分析。

## 🌟 核心架构与功能

本系统以 DeepSeek 为统一推理大脑，实现了任务分发与业务执行的物理隔离与松耦合：

- **主从协同多智能体架构 (Coordinator-Worker)**: 
  - **协调中枢 (Coordinator)**：负责理解多跳复杂用户意图并解构任务，通过 Tool Calling 机制并发调度底层多个专属执行智能体。
- **重型数据分析组 (SheetAgent Team)**: 针对复杂学情与成绩分析，内部构建严密工作流。查库智能体 (Informer) 将自然语言转化为 SQL 精准提取视图，规划智能体 (Planner) 在独立沙盒内编写执行 Python 脚本，完成深度的数值计算与动态 ECharts 图表渲染。
- **政策检索智能体 (Policy Worker)**: 针对毕业条件等规章咨询，结合 FAISS 向量库与本地 PDF，实现精准的 RAG 知识检索，消除 LLM 知识盲区。
- **多角色权限隔离**: 支持管理员、教师、学生多端登录，内置基于角色的严格数据越权拦截机制。

## 📁 目录结构说明

- `/app/agents/`: AI 核心大脑，包含顶层 `coordinator.py` 以及各个独立的专属执行组（`sheet_agent.py`, `policy_agent.py`, `data_agent.py`）。
- `/app/edge/`: 端侧 AI（MiniCPM-V 等）的图片 OCR 解析与信息提取。
- `/database/`: 数据库初始化和数据模拟脚本（使用 Faker 模拟）。
- `/docs/`: 参考文献与学校教务制度归档。
- `/static/` & `/app/templates/`: Flask 前端页面和资源（含 ECharts 图表渲染逻辑）。
- `.env`: **[请勿上传]** 存放系统环境变量。

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
该脚本会自动生成 1000 名学生及 1万多条成绩模拟记录：
```bash
python database/data_init.py
```

### 4. 运行系统
```bash
python run.py
```
然后访问 `http://127.0.0.1:5000` 即可登录体验。
