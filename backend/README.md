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
会话存在单进程内存中，使用一个 worker；重启会清空会话。
