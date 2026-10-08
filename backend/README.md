# 后端

Python + FastAPI，原生 Python 组织业务流程。

- app/api/：聊天、文档、评测报告与健康检查接口。
- app/rag/：PDF 提取、清洗、对齐、分块、embedding 与检索。
- app/guardrails/：原因分类、处理动作、输入/输出核查。
- app/services/：模型、会话、问答编排与指标记录。
- tests/：不依赖真实模型的逻辑测试。

FastAPI 入口为 app/main.py。requirements.txt 锁定当前验证过的依赖，requirements.in 保留直接依赖范围。

已有健康检查、资料状态、连接测试和 PDF 白名单接口。网页运行状态与 RAG 就绪分开：/health/live 返回200，/health/ready 当前返回503；/api/chat 尚未接入检索与生成。

从根目录执行 .venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000；或用 scripts/dev.sh。已有16项 unittest 检查，不调用模型。
