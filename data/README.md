# 数据目录

数据流：docs/保险原件.pdf → raw/逐页提取 → processed/清洗条款与分块 → chroma/向量索引。

## raw/

保存解析工具直接输出的逐页文本、布局信息或 MinerU 结果，不做清洗。用文档标识和版本/哈希建立子目录，记录文档哈希、工具版本、提取时间、从 1 开始的 PDF 实际页码，不覆盖旧结果。这里 raw 指解析后的原始数据，PDF 原件继续保存在 docs/，不重复维护。输出默认不提交 Git。

## processed/

保存 clauses.json、alignment.json、chunks.json 等清洗、对齐与分块结果。原文与清洗文本分别保留，脚注/条件有来源，记录处理版本；原文缺失/冲突明确标记，不补造证据。人工核对、无密钥的结构化结果可提交 Git。

## chroma/

生成的 Chroma 持久化索引，不提交 Git。Docker 后续挂载 volume。

目前已接收用户的 MinerU Markdown 和 JSON；raw/ 的原文件保持不变。

## 当前处理结果

- processed/mineru/：带页码和坐标的结构整理结果，以及人工核对的 corrections.json。
- processed/knowledge/evidence.json：原始提取、清洗文本、页码、坐标、脚注关联与待核对状态。
- processed/knowledge/chunks.json：用于后续 embedding 的规则分块；每块保留实际包含的 evidence_ids。
- processed/knowledge/parents.json：标题/段落归组，作为有预算限制的上下文补齐候选。
- processed/knowledge/alignment.json：按编号配对的双语脚注；不是全文语义对齐结果。
- processed/knowledge/changes.json 与 review.md：修复记录、原文冲突及局限。
- processed/knowledge/samples.md：三个实际样例供人工查看。

已建立12块小样本索引（data/chroma/pilot/），139块全量尚未建立。raw 文件默认忽略；重建需保留用户的原始 MinerU 导出，后续交付准备经过核对的结构化材料。

## reviewed/

`pilot_alignment.json` 保存实际核对的双语条款关系，与按编号自动配对的 alignment.json 区分。当前只覆盖利率、失业保障、周期提款选定的13组条款，全文仍需检查。简体中文不是额外的PDF来源。

运行 `.venv/bin/python scripts/check_alignment.py` 检查来源哈希、证据和页码、关键条件及三语言测试问题，并生成同目录的可读核对记录 `pilot_alignment.md`。哈希或关键条件变了，检查会失败，需要重新对照PDF核对。脚本只检查记录有效性，不自动判断双语含义。

小样本块和问题放在 `evaluation/retrieval_pilot.json`；准备好不等于已向量化或通过检索。
