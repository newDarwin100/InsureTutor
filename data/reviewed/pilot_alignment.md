# 小样本条款核对

核对日期：2026-10-08。这里只检查利率、失业、提款选定的正文和脚注。

13组条款，涉及27条证据；12组含义一致，1组有措辞差异。
由开发助手对照PDF页面图像核对，不是外部保险专家审校。编号脚注的自动配对结果仍留在 alignment.json，本文件记录实际核对结论。

PDF有繁体中文和英文来源。简体中文是提问和回答语言，不另造一份原文。

## 逐项记录

### premium-deductions · MATCHED

PDF实际页码：8（包含封面）。

**zh-Hant 来源**

- `p008-b002`：您的供款會於扣除任何適用的費用後，存入賬戶價值內，並獲享較一般銀行存款優厚的利息。 此外，我們保證無論經濟環境如何，於保單生效滿15年或以上，賬戶價值（包括撥入保單的利息及額外回報的總額）將不會少於每年以派息率 2.5%計算而累積的賬戶價值。

**en 来源**

- `p008-b003`：Your premium will be credited to the Account Value after deduction of any applicable charges and you will enjoy a relatively higher rate of return than most bank deposits.

**核对结果**

- 保费先扣除适用费用，再计入账户价值。

### account-value-floor · MATCHED

PDF实际页码：8（包含封面）。

**zh-Hant 来源**

- `p008-b002`：您的供款會於扣除任何適用的費用後，存入賬戶價值內，並獲享較一般銀行存款優厚的利息。 此外，我們保證無論經濟環境如何，於保單生效滿15年或以上，賬戶價值（包括撥入保單的利息及額外回報的總額）將不會少於每年以派息率 2.5%計算而累積的賬戶價值。

**en 来源**

- `p008-b004`：In addition, when a Policy has been in force for 15 years or more, the total interest and Extra Bonus credited to the Policy will be such that the Account Value is guaranteed to have accumulated to at least an amount as if the interest rate credited had been 2.5% p.a., regardless of the economic situation.

**核对结果**

- 保单生效满15年或以上。
- 保证比较对象是累计账户价值，不是每年保费回报率。
- 按假设每年2.5%派息累积的账户价值作为最低比较基础。

中文一段对应英文两段：费用和保证机制分别关联，不按段落数量硬配对。

### assumed-interest-rates · MATCHED

PDF实际页码：8（包含封面）。

**zh-Hant 来源**

- `p008-b005`：基本派息 (現時假設息率*） Base Crediting Interest (Current assumed rate*)
- `p008-b007`：4% 每年 p.a.
- `p008-b008`：額外利息 (現時假設息率*） Retrospective additional interest (Current assumed rate*)
- `p008-b009`：0.25% 每年 p.a.

**en 来源**

- `p008-b005`：基本派息 (現時假設息率*） Base Crediting Interest (Current assumed rate*)
- `p008-b007`：4% 每年 p.a.
- `p008-b008`：額外利息 (現時假設息率*） Retrospective additional interest (Current assumed rate*)
- `p008-b009`：0.25% 每年 p.a.

**核对结果**

- 图示基本派息率4%，额外利息率0.25%，均为假设年利率。

图示是同一组双语标签和共享数字，不复制成两份来源。

### assumed-rate-disclaimer · MATCHED

PDF实际页码：8（包含封面）。

**zh-Hant 来源**

- `p008-b011`：* 上述之現時假設基本派息率及現時假設額外利息息率為本冊子於2022年1月刊發時適用，並非保證， 日後或會更改。

**en 来源**

- `p008-b014`：* The current assumed base crediting interest rate and the current assumed retrospective additional interest rate are quoted as of the print date of this brochure in January 2022, and are not guaranteed. They are subject to change.

**核对结果**

- 数值是册子2022年1月刊发时的假设，并非保证，之后可能变化。
- 不得作为今天的报价。

### additional-interest-first-credit · MATCHED

PDF实际页码：8（包含封面）。

**zh-Hant 来源**

- `p008-b012`：^ 自保單第1年起計算至第20年，並於第20年年終撥入賬戶價值內。

**en 来源**

- `p008-b015`：^ This will be credited to the Account Value at the end of the 20th policy year, calculated from year 1 through 20.

**核对结果**

- 额外利息首笔按第1至20年计算，在第20年年终计入账户价值。

### additional-interest-later-credit · MATCHED

PDF实际页码：8（包含封面）。

**zh-Hant 来源**

- `p008-b013`：而由第20年起，其後每5年派發一次，將由每5年期的第1年起計算至第5年，並於第5年年終時撥入賬戶價值內。

**en 来源**

- `p008-b016`：# For every 5 years thereafter, this interest will be credited to the Account Value at the end of the 5-year period, calculated from year 1 through 5 of each period.

**核对结果**

- 此后每5年派发，按各5年期间计算，在该期间末计入。

### unemployment-special-grace · MATCHED

PDF实际页码：11（包含封面）。

**zh-Hant 来源**

- `p011-b003`：萬一投保人於保單有效期內不幸遭裁員或遣散，即可享有長達365日的「特惠寬限期」，於該期限內仍可繼續享有十足保障8。

**en 来源**

- `p011-b004`：Should the Policy Owner be made redundant, there is an option which allows suspension of premium payments for 365 days. During this entire "Special Grace Period", you will remain fully covered by the insurance8.

**核对结果**

- 适用对象是投保人被裁员或遣散，特惠宽限期最长365日。
- 范围须结合脚注8：只适用于基本计划。

### unemployment-basic-only · MATCHED

PDF实际页码：12（包含封面）。

**zh-Hant 来源**

- `p012-b009`：8. 失業保障只適用於基本計劃。

**en 来源**

- `p012-b020`：8. Unemployment Protection is only applicable to the Basic Plan.

**核对结果**

- 失业保障只适用于基本计划，不能扩展到所有附加保障。

### periodic-withdrawal-option · WORDING_DIFFERENCE

PDF实际页码：10（包含封面）。

**zh-Hant 来源**

- `p010-b005`：只要保單內已累積有足夠的現金價值，您可行使定期提款權益6，自由設定每月 / 每年提款金額及年期，讓各項理財安排（例如子女升學及退休等）更有規劃。此外，您亦可隨時提取部分現金價值7，以應不時之需。

**en 来源**

- `p010-b006`：When your Policy has accumulated a Cash Value, you can exercise the automatic periodic withdrawal option6 to withdraw a specified amount of Cash Value monthly / annually at preset time intervals, so that you can easily map out your financial needs, e.g. children's university education funds and retirement expenses. In addition, you can withdraw a portion of the Cash Value7 at any time to cope with emergencies.

**核对结果**

- 可设置按月或按年定期提款；具体资格和最低金额见脚注6。
- 正文也提及部分现金提款，费用见脚注7，不能与定期提款费用混同。

中文明确写足够的现金价值，英文未出现 sufficient。保留各自原文；不能声称逐字等价，也不能据英文推断任意金额均可提款。

### periodic-withdrawal-conditions · MATCHED

PDF实际页码：12（包含封面）。

**zh-Hant 来源**

- `p012-b007`：6. 定期提款權益只適用於生效滿10年或以上的保單，並可獲豁免支付提款費用。按現行規定，每月提款金額最低為500美元/4,000港元/4,000澳門元，提款年期最短一年；而每年提款金額最低為6,000美元/48,000 港元/48,000澳門元，提款年期最短三年。如欲更改已確認的定期提款權益，須支付手續費。

**en 来源**

- `p012-b018`：6. Automatic periodic withdrawal option is only applicable if the Policy has been in force for at least 10 years, the withdrawal charge will be waived. Current requirement on minimum monthly withdrawal amount is US$500/HK$4,000/MOP4,000, with minimum withdrawal period of one year; and the minimum annual withdrawal amount is US$6,000/HK$48,000/ MOP48,000, with minimum withdrawal period of three years. For any change after the application has been confirmed, a nominal fee will be levied.

**核对结果**

- 保单生效至少10年。
- 每月最低USD500/HKD4,000/MOP4,000，最短一年。
- 每年最低USD6,000/HKD48,000/MOP48,000，最短三年。
- 定期提款费用豁免；确认后更改安排仍收手续费。

英文HK$4,000已在之前按PDF视觉核对修复；原始提取仍保留。

### ordinary-withdrawal-fee · MATCHED

PDF实际页码：12（包含封面）。

**zh-Hant 来源**

- `p012-b008`：7. 現時提款費用每次25美元/200港元/200澳門元。

**en 来源**

- `p012-b019`：7. The current charge for each withdrawal is US$25/HK$ 200/MOP200.

**核对结果**

- 册子所列每次提款费USD25/HKD200/MOP200；定期提款豁免见脚注6。
- 费用不是当前报价；收费非保证见脚注10。

### charges-can-cause-lapse · MATCHED

PDF实际页码：10（包含封面）。

**zh-Hant 来源**

- `p010-b013`：提取現金、減低或暫停繳付保費，將會影響計劃所累積的現金價值，而每月費用仍會被扣除，如現金價值不足以支付每月費用時，保單便會終止而沒有任何價值。

**en 来源**

- `p010-b014`：Cash withdrawal, reducing the premium amount, or skipping premium payments will afect the accumulation of the Cash Value, while the monthly charges are still deductible. If the Cash Value is not suficient to cover the monthly charges, the Policy will lapse with zero value.

**核对结果**

- 提款、减保费或停缴会影响现金价值，每月费用仍扣除。
- 现金价值不足付费用存在失效且零价值风险，不能解释成永久保障。

这里只核对本页警示；若回答具体宽限期，还需检索第14页。英文提取有 afect/suficient 拼写漏字，不改保险含义。

### fees-can-change · MATCHED

PDF实际页码：12（包含封面）。

**zh-Hant 来源**

- `p012-b011`：10. 現時的收費標準並非保證，以及受制於本公司在提前一個月以書面通知後作出改變的全權酌情決定權。

**en 来源**

- `p012-b022`：10. The current scale of fees and charges is not guaranteed and is subject to the Company’s sole discretion to change with one-month prior written notice.

**核对结果**

- 收费标准非保证，公司可在提前一个月书面通知后变更。

## 下一步

小样本选9个目标检索块、3个干扰块，共12块；4种问题分别用简体、繁体、英文提问，共12题。
只准备好了文本和问题，还没向量化、没测召回。具体块和问题见 evaluation/retrieval_pilot.json。

## 尚未完成

- 仅核对列出的正文和脚注，全文其他条款仍未核对。
- 图示历史表格与全篇产品摘要尚未逐项对齐。
- 原文第17页金额冲突继续保留，不以本次核对消除。
- 不代表专业保险审校或模型回答已通过测试。
- 2026-10-08扩展清洗后重新检查：这27条证据的原文、清洗文本、页码和来源指针未变，更新整体证据哈希。
- 2026-10-08扩展清洗后重新检查：这27条证据的原文、清洗文本、页码和来源指针未变，更新整体证据哈希。
