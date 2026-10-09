# Embedding选择：同材料、同题对比

固定143块、12道三语言开发题、Top-K=5、Chroma cosine、同清洗及脚注关系。比较large/3072维与small/1536维的实际默认配置；模型和维度同时不同，不拆分归因。每题交替先查哪种模型，所有查询本轮未命中内存缓存。

| 配置 | 直接Recall@5均值 | 脚注关联后覆盖 | 最终回答上下文覆盖 | 查询均值 |
| --- | ---: | ---: | ---: | ---: |
| text-embedding-3-large | 87.50% | 100.00% | 100.00% | 294ms |
| text-embedding-3-small | 66.67% | 79.17% | 79.17% | 246ms |

## 为什么继续用large

small在简体和繁体的2.5%保证题里未命中所需条款，关联补齐后仍缺失；另有失业限制、英文假设利率遗漏。large也有直接Top-K漏脚注的情况，但本组已核对关系能补齐所需内容。small在两道中文4%题直接命中反而更好，所以不能说large每道题都更强。

这份材料最重要的是准确取回保证边界与适用条件。保留large，在成本与本组条件覆盖之间优先选择后者。small的平均查询时间本轮少约48ms，但这是24次交替顺序调用、单次观测，没有重复统计，不能承诺稳定提速。

small建立独立索引，实际向量化143块、18,309输入tokens，约3.65s；当前large索引复用，没有新large建库耗时。未切换应用的active索引。3072与1536默认维度依据[OpenAI官方说明](https://developers.openai.com/api/docs/guides/embeddings)。

## 逐题直接召回

| 问题 | large | small |
| --- | ---: | ---: |
| rate-guarantee-zh-Hans | 50% | 100% |
| rate-guarantee-zh-Hant | 50% | 100% |
| rate-guarantee-en | 100% | 50% |
| account-floor-zh-Hans | 100% | 0% |
| account-floor-zh-Hant | 100% | 0% |
| account-floor-en | 100% | 100% |
| unemployment-zh-Hans | 100% | 50% |
| unemployment-zh-Hant | 100% | 50% |
| unemployment-en | 50% | 50% |
| withdrawal-zh-Hans | 100% | 100% |
| withdrawal-zh-Hant | 100% | 100% |
| withdrawal-en | 100% | 100% |

原始排名、索引spec、usage和耗时见[JSON](embedding-comparison.json)。这是检索选择依据，不是答案正确率、LLM模型对比、固定窗口分块对比或生产压测。继续扩数据时需用新文档/题集验证。
