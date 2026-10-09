# 后端

Python 3.12 + FastAPI，入口 `app/main.py`。

- `app/rag/`：清洗、分块、显式 embedding 与版本化 Chroma 索引。
- `app/guardrails/`：原因分类、输入规则、输出引用和冲突检查。
- `app/services/`：模型、答案编排、会话、追问改写及只读评测。
- `tests/`：无需真实模型的回归测试。

`/api/chat` 接通 RAG；`/api/conversations` 创建会话，凭证通过请求头传递。
`/api/evaluations` 只读保存报告，PDF 接口只开放固定文档。
live 检查进程，ready 检查本地配置、来源和索引，不探测模型。

requirements.txt 锁定依赖，requirements.in 保留直接依赖。
从根目录运行 `bash scripts/dev.sh`；首次建库与 Docker 见 [README](../README.md)。
会话完整记录存在SQLite（data/history/chats.sqlite3），使用一个worker；刷新/重启后会恢复，模型近期上下文仍限制8轮/24,000字符。内存缓存闲置30分钟后淘汰，但不删除聊天记录。

`POST /api/workspaces`创建浏览器列表凭证；`GET /api/conversations`用X-Workspace-Token列出自己的会话。会话创建可带这个头关联列表；current的GET/PATCH/DELETE用X-Conversation-Token读取、改名和删除。凭证不放URL。数据库不从HTTP开放，也不加入Git/镜像。

页面发送language=auto，后端用OpenCC字典本地识别简繁/英文；少数共享汉字沿用本会话最近中文类型。明确language参数仍用于固定评测。
