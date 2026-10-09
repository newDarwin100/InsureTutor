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
`answer_regression.json` 已准备26道固定参考题，覆盖复合题三语言、保证误解、失业、月/年追问、普通提款费、失效、末期病症及除外期、冷静期、期满、原文冲突、无据与安全。预期事实先基于原文写好，不读取私人聊天记录。

`scripts/run_answer_regression.py` 默认只校验题集；加 `--run` 才真实生成与核对。输出保存引用结构检查、阶段耗时、usage、模型诊断及待人工核对字段。模型核对通过不等于人工确认，拒绝题没有首字答案计时。已有输出禁止覆盖，复测须另指定文件。

`scripts/compare_embeddings.py --run` 比较同143块、同12道三语言题的 large/3072维与 small/1536维；small放独立目录，不切换应用索引。交替查询顺序，分别报告直接召回、脚注关联及最终上下文覆盖。样本有限，时延仅供观察，不据单轮结果宣称稳定性能优势。官方接口依据：[OpenAI embeddings](https://developers.openai.com/api/docs/guides/embeddings)。

两组首轮已真实运行：[26题原文核对](results/answer-regression.md)、[small/large检索对比](results/embedding-comparison.md)。26题动作符合24题，但逐题核对仍发现显示与条件问题，不作为24/26答案正确率。基于12题条件覆盖保留large。原始失败不覆盖。

四题保存输出的[免费回放](results/answer-replay.json)只验证引用显示、简繁转换和冲突判定修复，不能计成新的模型生成。[五题定点真实复测](results/answer-regression-fixes.md)已执行：R02/R10/R11/R15符合，R13仍失败且继续修正范围指令；原失败和明显偏慢的API计时都保留。全部核对是开发期间Codex对照原文，未经独立保险专业审校。
付费入口及发送数据说明见 [README](../README.md)；不要覆盖结果美化指标。
