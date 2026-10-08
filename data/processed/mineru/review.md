# MinerU 初步结构检查

页数：20；内容块：{'image': 32, 'title': 72, 'text': 226, 'chart': 1, 'table': 9}。

本结果只整理结构，尚未清洗、修正、对齐语言或构建检索分块。
PDF 页码从 1 开始，包含封面；MinerU page_idx 从 0 开始。
保留正文、标题、表格 HTML、单元格和合并属性、坐标、被解析器丢弃的块及源 JSON 路径。
language_hint 只用于辅助筛选，中文未自动判定简繁；含货币缩写的中文可能标为 mixed。

## 自动标记的待核对项

| PDF 页 | 块 | 原因 |
| --- | --- | --- |
| 8 | p008-b002 | CONTROL_CHARACTER |
| 12 | p012-b005 | CONTROL_CHARACTER |
| 12 | p012-b006 | CONTROL_CHARACTER |
| 12 | p012-b018 | POSSIBLE_MISSING_CURRENCY_AMOUNT |
| 16 | p016-b002 | MERGED_PERCENT_VALUES |
| 17 | p017-b001 | POSSIBLE_MISSING_CURRENCY_AMOUNT |

标记只提示可能的问题，不代表全文已检查，也不自动给出正确替代值。
下一步：按原 PDF 核对这些项、恢复阅读关系、关联中英文条款和脚注，再建立测试题。
