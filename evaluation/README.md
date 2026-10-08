# 评测

questions.json 已建立首批 10 个参考案例，保存语言、历史、预期事实、条件、证据组、禁止错误和安全动作。覆盖利率保证、提款、失效风险、三语言、多轮、原文冲突、注入泄密与个人建议。当前只是参考题，未运行真实模型。

results/ 将保存真实运行结果、模型配置、耗时、usage、引用和人工核对结果，供看板读取。只保存评测题，不保存普通用户会话；当前没有真实检索或模型结果。

## 验证题集

```bash
.venv/bin/python scripts/evaluate_retrieval.py
```

检查引用证据 ID 和实际页码，不调用模型，不产生虚构评测分数。

## 后续评估实际检索结果

检索器输出 JSON 数组，每项包含 case_id 和按排名排列的 ranked_chunk_ids，运行：

```bash
.venv/bin/python scripts/evaluate_retrieval.py --results path/to/actual-rankings.json
```

scoring.py 将原始 Recall@5 与补齐脚注后的覆盖率分开；中英可替代证据作为同一组计分。安全短路题无检索分母，显示 null；重复或未知 ID 报错，缺失案例列出。答案和引用语义准确性仍需独立人工核对，不从检索命中推断。

题集包含 development 和 validation；validation 不用于反复调参。后续扩到 20–30 题，并补充越界、无依据、正常问题误拒和更多跨语言案例。
