# 评测

questions.json 保存首批10道参考题，含必要事实、限制、证据组和禁止错误。
retrieval_pilot.json 保存三语言小样本配置。
results/ 保存真实固定测试的排名、耗时、usage 和生成结果，普通用户问答不落盘。

免费检查：`scripts/evaluate_retrieval.py` 和 `scripts/check_full_alignment.py`。
如已有实际排名，使用 `scripts/evaluate_retrieval.py --results path/to/rankings.json`。

直接 Recall@5 和关联补齐覆盖率分别报告。检索命中、模型核对通过、人工确认正确是不同结果。

## 已保存结果

- pilot-large.json：12块小库、12道三语言检索题。
- full-large.json / .md：143块全文、12道三语言题和8道参考检索题，2道安全题未执行。
- single-turn.json、single-turn-retry.json / single-turn.md：最初两题和一次提款重测，保留失败。
- compound-question.json：复合题。模型核对通过后人工发现漏条件，不能计为人工验收通过。

新增 demo-answers.json / .md 保存6道页面示例的真实回归和原失败尝试；人工核对关键事实，未用来计算整体正确率。

看板仍读取原五份 JSON，共38行历史结果，不重新付费测试。缓存保留原始计时，未知数据为空。
完整20–30题答案验收、真实多轮/安全校准和模型对比待完成。
付费入口及发送数据说明见 [README](../README.md)；不要覆盖结果美化指标。
