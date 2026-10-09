# 脚本入口

从项目根目录运行。完整启动说明见 [README](../README.md)。

| 脚本 | 用途 | 是否调用模型 |
| --- | --- | --- |
| `start.sh` | Docker 构建、初始化/复用索引、等待 RAG 就绪 | 索引缺失或版本变化时 embedding |
| `container_entrypoint.py` | 容器来源核对、索引初始化、启动 FastAPI | 同上 |
| `dev.sh` | 启动已安装的本地前后端；检查版本和端口 | 否 |
| `build_index.py --full` | 验证全文核对记录，建库或复用 | 只向量化缺失块 |
| `search_knowledge.py "问题"` | 查询当前索引 | 查询 embedding |
| `run_retrieval_pilot.py` / `run_full_retrieval.py` | 小库 / 全文检索评测 | 缺失索引或查询缓存时调用 |
| `check_answers.py --run` | 固定题真实生成与核对 | 是 |
| `check_demo_examples.py --run` | 6道页面示例与追问真实回归；重测保留前次结果 | 是 |
| `run_answer_regression.py` | 校验26道固定参考题；`--run`真实生成/核对并保留逐题结果 | 仅`--run`调用 |
| `compare_embeddings.py` | 同143块、12道题比较small/large；独立测试索引 | 仅`--run`调用embedding |
| `smoke_test.py` | API 连通性测试 | 是 |
| `check_local.py` | 页面、健康、PDF Range、路径隔离 | 否 |
| `check_full_alignment.py` / `check_alignment.py` | 全文 / 小样本来源与对应检查 | 否 |
| `evaluate_retrieval.py` | 验证参考题，或给实际排名计分 | 否 |
| `normalize_mineru.py` | 原始 JSON 整理与已核对修复 | 否 |
| `prepare_knowledge.py` | 规则清洗、表格拆行、关联和分块 | 否 |
| `extract_pdf.py` | pypdf 提取基线，需另装 pypdf | 否 |

重新处理原始数据需要本机的 MinerU JSON；普通启动不需要 raw 数据。
缓存计时是历史测量，不是新的 API 测速。不要用模拟数据替换真实报告。
