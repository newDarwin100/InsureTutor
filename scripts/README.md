# 脚本

已有 smoke_test.py：读取本地 .env，测试模型连通性。

已有 dev.sh 同时启动前后端，start.sh 构建并启动 Docker 应用，check_local.py 检查正在运行的最小链路。当前机器未安装 Docker，start.sh 尚未做容器验收。向量索引与真实模型评测入口尚未实现；evaluate_retrieval.py 可验证参考题或给实际排名计分，默认不调用模型。

## 已有 PDF 处理入口

- extract_pdf.py：pypdf 逐页提取基线，需要 pypdf；不做清洗。
- normalize_mineru.py：读取用户导出的 MinerU JSON，用 Python 标准库整理页码、文本块、表格与待核对标记。

运行 MinerU 结构整理：

```bash
.venv/bin/python scripts/normalize_mineru.py
```

默认输出 data/processed/mineru/pages.json、manifest.json 和 review.md。它们是未完成清洗的中间数据，不是已验收知识库；保留原始 JSON 不动。

## 规则清洗和分块

```bash
.venv/bin/python scripts/prepare_knowledge.py
.venv/bin/python -m unittest discover -s backend/tests -v
```

实现位于 backend/app/rag/preprocess.py，仅用 Python 标准库，不调用模型。
输出 data/processed/knowledge/ 下的 evidence.json、parents.json、chunks.json、alignment.json、changes.json、omitted_blocks.json、manifest.json 和 review.md。

人工核对的修复与明确关联配置在 data/processed/mineru/corrections.json，绑定输入哈希；原数据变化时必须重新核对。原始提取仍保留，不能把清洗文本误称为未经处理的引用原文。
默认分块上限 1200 字符，超长段落 overlap 120 字符；这不是 token 计数。按标题归组并合并短段落，表格按行保留类别与表头，编号脚注关联正文。简繁转换和全文双语语义核对尚未实现，尚未评测召回。
