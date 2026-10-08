# 全文提取数据核对记录

依据MinerU的正文、表格、discarded_blocks核对。PDF为20页，页码含封面。
当前292条证据都有对应关系或用途说明；185个分组包含正文对应、共享双语表格和上下文。简体中文用于提问/回答，原文仍为繁体和英文。

这不是“PDF每个图像字符都已入库”，也不是专业保险审校。

## 这次修了什么

- 第19页英文免责声明原本在discarded_blocks；恢复为p019-d001。
- 恢复封面产品类型、第3页退休标签、第20页客服地址，原JSON和来源指针保留。
- 第18页表格第一行是条款内容，不应成为后续行的表头；去掉错误继承的退保说明/投保年龄前缀。
- 增补保障增值、保证可保、末期病症的条件与不保事项关联。

## 不能自行统一的内容

- periodic-withdrawal-option（PDF [10]）：中文明确写足够的现金价值，英文未出现 sufficient。保留各自原文；不能声称逐字等价，也不能据英文推断任意金额均可提款。
- page-10-clause-8（PDF [10]）：中文强调足够现金价值，英文只写已累积现金价值；结合每月费用及失效风险说明。
- page-11-clause-9（PDF [11]）：中文65岁或以前包含65岁，英文before the age of 65不包含65岁；不能确认65岁生日边界，需核对正式保单。
- page-15-clause-11（PDF [15]）：中文写曾获或将获赔偿不退款，英文另外明确impending；回答保留英文完整限制。21日以交付保单或通知较早者计，退保费与冷静期不混同。
- terminal-summary（PDF [16]）：中文摘要写附加保障如适用，英文摘要未重复条件；第11页正文及附注9保留if any和终止条件。
- sum-insured-change-conflict（PDF [17]）：中文HKD40,000/MOP400,000；英文HKD400,000/MOP40,000，保留两种说法。

## 图像与历史信息的限制

- JSON将条形图保留为图片，图中的43/36/21%未进入文本；历史图表数据不得补猜。
- JSON提供部分时间线文字，但年龄/阶段对应未完全结构化；不根据残片给完整人生阶段表。
- 比较表的勾叉属于图片，正文保留；不将万用寿险与传统寿险图示差异推断为本产品条款。
- 708,800×2.75%=19,492是示例；共享美元符号未指定币种，不自行改成港币。
- 利率说明为2022年1月，公司介绍有2025年排名信息；不能用一个日期覆盖所有内容，也不能说是今天的利率/地址。

## 对应表

同一ID同时出现在两栏，表示原块本身包含双语或共享数字，不是新增了一份译文。

| 分组 | 状态 | 繁体来源 | 英文来源 | PDF页 |
| --- | --- | --- | --- | --- |
| premium-deductions | MATCHED | p008-b002 | p008-b003 | [8] |
| account-value-floor | MATCHED | p008-b002 | p008-b004 | [8] |
| assumed-interest-rates | MATCHED | p008-b005, p008-b007, p008-b008, p008-b009 | p008-b005, p008-b007, p008-b008, p008-b009 | [8] |
| assumed-rate-disclaimer | MATCHED | p008-b011 | p008-b014 | [8] |
| additional-interest-first-credit | MATCHED | p008-b012 | p008-b015 | [8] |
| additional-interest-later-credit | MATCHED | p008-b013 | p008-b016 | [8] |
| unemployment-special-grace | MATCHED | p011-b003 | p011-b004 | [11] |
| unemployment-basic-only | MATCHED | p012-b009 | p012-b020 | [12] |
| periodic-withdrawal-option | WORDING_DIFFERENCE | p010-b005 | p010-b006 | [10] |
| periodic-withdrawal-conditions | MATCHED | p012-b007 | p012-b018 | [12] |
| ordinary-withdrawal-fee | MATCHED | p012-b008 | p012-b019 | [12] |
| charges-can-cause-lapse | MATCHED | p010-b013 | p010-b014 | [10] |
| fees-can-change | MATCHED | p012-b011 | p012-b022 | [12] |
| page-02-clause-1 | MATCHED | p002-b001 | p002-b002 | [2] |
| page-03-clause-1 | MATCHED | p003-b001 | p003-b002 | [3] |
| page-04-clause-2 | MATCHED | p004-b002 | p004-b003 | [4] |
| page-04-clause-4 | MATCHED | p004-b004 | p004-b005 | [4] |
| page-04-clause-7 | MATCHED | p004-b007 | p004-b008 | [4] |
| page-04-clause-10 | MATCHED | p004-b010 | p004-b011 | [4] |
| page-04-clause-13 | MATCHED | p004-b013 | p004-b014 | [4] |
| page-04-clause-16 | MATCHED | p004-b016 | p004-b017 | [4] |
| page-04-clause-19 | MATCHED | p004-b019 | p004-b020 | [4] |
| page-06-clause-2 | MATCHED | p006-b002 | p006-b003 | [6] |
| page-06-clause-5 | MATCHED | p006-b005 | p006-b006 | [6] |
| page-06-clause-8 | MATCHED | p006-b008 | p006-b009 | [6] |
| page-07-clause-3 | MATCHED | p007-b003 | p007-b005 | [7] |
| page-09-clause-2 | MATCHED | p009-b002 | p009-b003 | [9] |
| page-09-clause-15 | MATCHED | p009-b015 | p009-b016 | [9] |
| page-09-clause-22 | MATCHED | p009-b022 | p009-b023 | [9] |
| page-10-clause-2 | MATCHED | p010-b002 | p010-b003 | [10] |
| page-11-clause-6 | MATCHED | p011-b006 | p011-b007 | [11] |
| page-11-clause-11 | MATCHED | p011-b011 | p011-b016 | [11] |
| page-13-clause-3 | MATCHED | p013-b003 | p013-b024 | [13] |
| page-13-clause-4 | MATCHED | p013-b004 | p013-b025 | [13] |
| page-13-clause-5 | MATCHED | p013-b005 | p013-b026 | [13] |
| page-13-clause-6 | MATCHED | p013-b006 | p013-b027 | [13] |
| page-13-clause-7 | MATCHED | p013-b007 | p013-b028 | [13] |
| page-13-clause-8 | MATCHED | p013-b008 | p013-b029 | [13] |
| page-13-clause-10 | MATCHED | p013-b010 | p013-b031 | [13] |
| page-13-clause-11 | MATCHED | p013-b011 | p013-b032 | [13] |
| page-13-clause-12 | MATCHED | p013-b012 | p013-b033 | [13] |
| page-13-clause-14 | MATCHED | p013-b014 | p013-b035 | [13] |
| page-13-clause-15 | MATCHED | p013-b015 | p013-b036 | [13] |
| page-14-clause-3 | MATCHED | p014-b003 | p014-b031 | [14] |
| page-14-clause-5 | MATCHED | p014-b005 | p014-b033 | [14] |
| page-14-clause-6 | MATCHED | p014-b006 | p014-b034 | [14] |
| page-14-clause-7 | MATCHED | p014-b007 | p014-b035 | [14] |
| page-14-clause-8 | MATCHED | p014-b008 | p014-b036 | [14] |
| page-14-clause-9 | MATCHED | p014-b009 | p014-b037 | [14] |
| page-14-clause-10 | MATCHED | p014-b010 | p014-b038 | [14] |
| page-14-clause-12 | MATCHED | p014-b012 | p014-b040 | [14] |
| page-14-clause-14 | MATCHED | p014-b014 | p014-b042 | [14] |
| page-14-clause-16 | MATCHED | p014-b016 | p014-b044 | [14] |
| page-14-clause-18 | MATCHED | p014-b018 | p014-b046 | [14] |
| page-14-clause-20 | MATCHED | p014-b020 | p014-b048 | [14] |
| page-14-clause-22 | MATCHED | p014-b022 | p014-b050 | [14] |
| page-14-clause-23 | MATCHED | p014-b023 | p014-b051 | [14] |
| page-14-clause-24 | MATCHED | p014-b024 | p014-b052 | [14] |
| page-14-clause-25 | MATCHED | p014-b025 | p014-b053 | [14] |
| page-14-clause-26 | MATCHED | p014-b026 | p014-b054 | [14] |
| page-14-clause-27 | MATCHED | p014-b027 | p014-b055 | [14] |
| page-14-clause-28 | MATCHED | p014-b028 | p014-b056 | [14] |
| page-15-clause-2 | MATCHED | p015-b002 | p015-b018 | [15] |
| page-15-clause-7 | MATCHED | p015-b007 | p015-b021 | [15] |
| page-15-clause-9 | MATCHED | p015-b009 | p015-b023 | [15] |
| page-15-clause-13 | MATCHED | p015-b013 | p015-b027 | [15] |
| page-15-clause-14 | MATCHED | p015-b014 | p015-b028 | [15] |
| page-15-clause-16 | MATCHED | p015-b016 | p015-b030 | [15] |
| page-20-clause-2 | MATCHED | p020-b002 | p020-b004 | [20] |
| page-20-clause-3 | MATCHED | p020-b003 | p020-b005 | [20] |
| page-20-clause-11 | MATCHED | p020-b011 | p020-b013 | [20] |
| page-20-clause-12 | MATCHED | p020-b012 | p020-b014 | [20] |
| page-10-clause-8 | WORDING_DIFFERENCE | p010-b008 | p010-b009 | [10] |
| page-11-clause-9 | CONFLICT | p011-b009 | p011-b015 | [11] |
| page-13-clause-16 | MATCHED | p013-b016 | p013-b037, p013-b038 | [13] |
| page-13-clause-17 | MATCHED | p013-b017, p013-b019 | p013-b040, p013-b041 | [13] |
| page-13-clause-21 | MATCHED | p013-b021 | p013-b043 | [13] |
| page-15-clause-4 | MATCHED | p015-b004, p015-b005, p015-b006 | p015-b020 | [15] |
| page-15-clause-11 | WORDING_DIFFERENCE | p015-b011 | p015-b025 | [15] |
| brochure-scope | MATCHED | p019-b001 | p019-d001 | [19] |
| full-note-01 | MATCHED | p012-b002 | p012-b013 | [12] |
| full-note-02 | MATCHED | p012-b003 | p012-b014 | [12] |
| full-note-03 | MATCHED | p012-b004 | p012-b015 | [12] |
| full-note-04 | MATCHED | p012-b005 | p012-b016 | [12] |
| full-note-05 | MATCHED | p012-b006 | p012-b017 | [12] |
| full-note-07 | MATCHED | p012-b008 | p012-b019 | [12] |
| full-note-09 | MATCHED | p012-b010 | p012-b021 | [12] |
| shared-p001-d002 | SHARED_BILINGUAL_SOURCE | p001-d002 | p001-d002 | [1] |
| shared-p003-d001 | SHARED_BILINGUAL_SOURCE | p003-d001 | p003-d001 | [3] |
| shared-p020-d001 | SHARED_BILINGUAL_SOURCE | p020-d001 | p020-d001 | [20] |
| shared-p002-b004 | SHARED_BILINGUAL_SOURCE | p002-b004 | p002-b004 | [2] |
| shared-p002-b005 | SHARED_BILINGUAL_SOURCE | p002-b005 | p002-b005 | [2] |
| shared-p002-b006 | SHARED_BILINGUAL_SOURCE | p002-b006 | p002-b006 | [2] |
| shared-p002-b007 | SHARED_BILINGUAL_SOURCE | p002-b007 | p002-b007 | [2] |
| shared-p003-b004 | SHARED_BILINGUAL_SOURCE | p003-b004 | p003-b004 | [3] |
| shared-p003-b006 | SHARED_BILINGUAL_SOURCE | p003-b006 | p003-b006 | [3] |
| shared-p003-b009 | SHARED_BILINGUAL_SOURCE | p003-b009 | p003-b009 | [3] |
| shared-p005-b004 | SHARED_BILINGUAL_SOURCE | p005-b004 | p005-b004 | [5] |
| shared-p005-b005 | SHARED_BILINGUAL_SOURCE | p005-b005 | p005-b005 | [5] |
| shared-p005-b008 | SHARED_BILINGUAL_SOURCE | p005-b008 | p005-b008 | [5] |
| shared-p005-b010 | SHARED_BILINGUAL_SOURCE | p005-b010 | p005-b010 | [5] |
| shared-p005-b011 | SHARED_BILINGUAL_SOURCE | p005-b011 | p005-b011 | [5] |
| shared-p005-b015 | SHARED_BILINGUAL_SOURCE | p005-b015 | p005-b015 | [5] |
| shared-p005-b016 | SHARED_BILINGUAL_SOURCE | p005-b016 | p005-b016 | [5] |
| shared-p005-b017 | SHARED_BILINGUAL_SOURCE | p005-b017 | p005-b017 | [5] |
| shared-p005-b021 | SHARED_BILINGUAL_SOURCE | p005-b021 | p005-b021 | [5] |
| shared-p005-b022 | SHARED_BILINGUAL_SOURCE | p005-b022 | p005-b022 | [5] |
| shared-p005-b023 | SHARED_BILINGUAL_SOURCE | p005-b023 | p005-b023 | [5] |
| shared-p005-b030 | SHARED_BILINGUAL_SOURCE | p005-b030 | p005-b030 | [5] |
| shared-p006-b011 | SHARED_BILINGUAL_SOURCE | p006-b011 | p006-b011 | [6] |
| shared-p007-b011 | SHARED_BILINGUAL_SOURCE | p007-b011 | p007-b011 | [7] |
| shared-p007-b012 | SHARED_BILINGUAL_SOURCE | p007-b012 | p007-b012 | [7] |
| shared-p007-b013 | SHARED_BILINGUAL_SOURCE | p007-b013 | p007-b013 | [7] |
| shared-p007-b015 | SHARED_BILINGUAL_SOURCE | p007-b015 | p007-b015 | [7] |
| shared-p009-b004 | SHARED_BILINGUAL_SOURCE | p009-b004 | p009-b004 | [9] |
| shared-p009-b006 | SHARED_BILINGUAL_SOURCE | p009-b006 | p009-b006 | [9] |
| shared-p009-b007 | SHARED_BILINGUAL_SOURCE | p009-b007 | p009-b007 | [9] |
| shared-p009-b008 | SHARED_BILINGUAL_SOURCE | p009-b008 | p009-b008 | [9] |
| shared-p009-b009 | SHARED_BILINGUAL_SOURCE | p009-b009 | p009-b009 | [9] |
| shared-p009-b010 | SHARED_BILINGUAL_SOURCE | p009-b010 | p009-b010 | [9] |
| shared-p009-b011 | SHARED_BILINGUAL_SOURCE | p009-b011 | p009-b011 | [9] |
| shared-p009-b012 | SHARED_BILINGUAL_SOURCE | p009-b012 | p009-b012 | [9] |
| shared-p009-b013 | SHARED_BILINGUAL_SOURCE | p009-b013 | p009-b013 | [9] |
| shared-p009-b018 | SHARED_BILINGUAL_SOURCE | p009-b018 | p009-b018 | [9] |
| shared-p009-b019 | SHARED_BILINGUAL_SOURCE | p009-b019 | p009-b019 | [9] |
| shared-p009-b020 | SHARED_BILINGUAL_SOURCE | p009-b020 | p009-b020 | [9] |
| shared-p009-b021 | SHARED_BILINGUAL_SOURCE | p009-b021 | p009-b021 | [9] |
| shared-p020-b015 | SHARED_BILINGUAL_SOURCE | p020-b015 | p020-b015 | [20] |
| page-05-clause-27 | MATCHED | p005-b027 | p005-b028 | [5] |
| shared-p007-b001-t1-r1 | SHARED_BILINGUAL_SOURCE | p007-b001-t1-r1 | p007-b001-t1-r1 | [7] |
| shared-p007-b001-t1-r2 | SHARED_BILINGUAL_SOURCE | p007-b001-t1-r2 | p007-b001-t1-r2 | [7] |
| shared-p007-b001-t1-r3 | SHARED_BILINGUAL_SOURCE | p007-b001-t1-r3 | p007-b001-t1-r3 | [7] |
| shared-p007-b001-t1-r4 | SHARED_BILINGUAL_SOURCE | p007-b001-t1-r4 | p007-b001-t1-r4 | [7] |
| context-p008-b001-t1-r1 | CONTEXT_ONLY | p008-b001-t1-r1 |  | [8] |
| shared-p008-b001-t1-r2 | SHARED_BILINGUAL_SOURCE | p008-b001-t1-r2 | p008-b001-t1-r2 | [8] |
| shared-p008-b001-t1-r3 | SHARED_BILINGUAL_SOURCE | p008-b001-t1-r3 | p008-b001-t1-r3 | [8] |
| shared-p008-b001-t1-r4 | SHARED_BILINGUAL_SOURCE | p008-b001-t1-r4 | p008-b001-t1-r4 | [8] |
| context-p008-b001-t1-r5 | CONTEXT_ONLY | p008-b001-t1-r5 |  | [8] |
| context-p008-b001-t1-r6 | CONTEXT_ONLY | p008-b001-t1-r6 |  | [8] |
| context-p008-b001-t1-r7 | CONTEXT_ONLY | p008-b001-t1-r7 |  | [8] |
| context-p008-b001-t1-r8 | CONTEXT_ONLY | p008-b001-t1-r8 |  | [8] |
| context-p008-b001-t1-r9 | CONTEXT_ONLY | p008-b001-t1-r9 |  | [8] |
| context-p008-b001-t1-r10 | CONTEXT_ONLY | p008-b001-t1-r10 |  | [8] |
| context-p008-b001-t1-r11 | CONTEXT_ONLY | p008-b001-t1-r11 |  | [8] |
| context-p008-b001-t1-r12 | CONTEXT_ONLY | p008-b001-t1-r12 |  | [8] |
| context-p008-b001-t1-r13 | CONTEXT_ONLY | p008-b001-t1-r13 |  | [8] |
| shared-p009-b017-t1-r1 | SHARED_BILINGUAL_SOURCE | p009-b017-t1-r1 | p009-b017-t1-r1 | [9] |
| shared-p009-b017-t1-r2 | SHARED_BILINGUAL_SOURCE | p009-b017-t1-r2 | p009-b017-t1-r2 | [9] |
| shared-p009-b017-t1-r3 | SHARED_BILINGUAL_SOURCE | p009-b017-t1-r3 | p009-b017-t1-r3 | [9] |
| shared-p009-b017-t1-r4 | SHARED_BILINGUAL_SOURCE | p009-b017-t1-r4 | p009-b017-t1-r4 | [9] |
| shared-p009-b017-t1-r5 | SHARED_BILINGUAL_SOURCE | p009-b017-t1-r5 | p009-b017-t1-r5 | [9] |
| shared-p009-b017-t1-r6 | SHARED_BILINGUAL_SOURCE | p009-b017-t1-r6 | p009-b017-t1-r6 | [9] |
| shared-p016-b002-t1-r1 | SHARED_BILINGUAL_SOURCE | p016-b002-t1-r1 | p016-b002-t1-r1 | [16] |
| shared-p016-b002-t1-r2 | SHARED_BILINGUAL_SOURCE | p016-b002-t1-r2 | p016-b002-t1-r2 | [16] |
| shared-p016-b002-t1-r3 | SHARED_BILINGUAL_SOURCE | p016-b002-t1-r3 | p016-b002-t1-r3 | [16] |
| shared-p016-b002-t1-r4 | SHARED_BILINGUAL_SOURCE | p016-b002-t1-r4 | p016-b002-t1-r4 | [16] |
| shared-p016-b002-t1-r5 | SHARED_BILINGUAL_SOURCE | p016-b002-t1-r5 | p016-b002-t1-r5 | [16] |
| shared-p016-b002-t1-r6 | SHARED_BILINGUAL_SOURCE | p016-b002-t1-r6 | p016-b002-t1-r6 | [16] |
| shared-p016-b002-t1-r7 | SHARED_BILINGUAL_SOURCE | p016-b002-t1-r7 | p016-b002-t1-r7 | [16] |
| shared-p016-b002-t1-r8 | SHARED_BILINGUAL_SOURCE | p016-b002-t1-r8 | p016-b002-t1-r8 | [16] |
| shared-p016-b002-t1-r9 | SHARED_BILINGUAL_SOURCE | p016-b002-t1-r9 | p016-b002-t1-r9 | [16] |
| shared-p016-b002-t1-r10 | SHARED_BILINGUAL_SOURCE | p016-b002-t1-r10 | p016-b002-t1-r10 | [16] |
| terminal-summary | WORDING_DIFFERENCE | p016-b002-t1-r11 | p016-b002-t1-r11 | [16] |
| shared-p016-b002-t1-r12 | SHARED_BILINGUAL_SOURCE | p016-b002-t1-r12 | p016-b002-t1-r12 | [16] |
| shared-p016-b002-t1-r13 | SHARED_BILINGUAL_SOURCE | p016-b002-t1-r13 | p016-b002-t1-r13 | [16] |
| shared-p016-b002-t1-r14 | SHARED_BILINGUAL_SOURCE | p016-b002-t1-r14 | p016-b002-t1-r14 | [16] |
| shared-p016-b002-t1-r15 | SHARED_BILINGUAL_SOURCE | p016-b002-t1-r15 | p016-b002-t1-r15 | [16] |
| shared-p016-b002-t1-r16 | SHARED_BILINGUAL_SOURCE | p016-b002-t1-r16 | p016-b002-t1-r16 | [16] |
| shared-p017-b001-t1-r1 | SHARED_BILINGUAL_SOURCE | p017-b001-t1-r1 | p017-b001-t1-r1 | [17] |
| shared-p017-b001-t1-r2 | SHARED_BILINGUAL_SOURCE | p017-b001-t1-r2 | p017-b001-t1-r2 | [17] |
| shared-p017-b001-t1-r3 | SHARED_BILINGUAL_SOURCE | p017-b001-t1-r3 | p017-b001-t1-r3 | [17] |
| shared-p017-b001-t1-r4 | SHARED_BILINGUAL_SOURCE | p017-b001-t1-r4 | p017-b001-t1-r4 | [17] |
| shared-p017-b001-t1-r5 | SHARED_BILINGUAL_SOURCE | p017-b001-t1-r5 | p017-b001-t1-r5 | [17] |
| sum-insured-change-conflict | CONFLICT | p017-b001-t1-r6 | p017-b001-t1-r6 | [17] |
| shared-p017-b001-t1-r7 | SHARED_BILINGUAL_SOURCE | p017-b001-t1-r7 | p017-b001-t1-r7 | [17] |
| shared-p017-b001-t1-r8 | SHARED_BILINGUAL_SOURCE | p017-b001-t1-r8 | p017-b001-t1-r8 | [17] |
| shared-p017-b001-t1-r9 | SHARED_BILINGUAL_SOURCE | p017-b001-t1-r9 | p017-b001-t1-r9 | [17] |
| shared-p018-b001-t1-r1 | SHARED_BILINGUAL_SOURCE | p018-b001-t1-r1 | p018-b001-t1-r1 | [18] |
| shared-p018-b001-t1-r2 | SHARED_BILINGUAL_SOURCE | p018-b001-t1-r2 | p018-b001-t1-r2 | [18] |
| shared-p018-b002-t1-r1 | SHARED_BILINGUAL_SOURCE | p018-b002-t1-r1 | p018-b002-t1-r1 | [18] |
| shared-p018-b002-t1-r2 | SHARED_BILINGUAL_SOURCE | p018-b002-t1-r2 | p018-b002-t1-r2 | [18] |
| shared-p018-b002-t1-r3 | SHARED_BILINGUAL_SOURCE | p018-b002-t1-r3 | p018-b002-t1-r3 | [18] |
| investment-allocation-1 | MATCHED | p013-b013-t1-r1 | p013-b034-t1-r1 | [13] |
| investment-allocation-2 | MATCHED | p013-b013-t1-r2 | p013-b034-t1-r2 | [13] |
| investment-allocation-3 | MATCHED | p013-b013-t1-r3 | p013-b034-t1-r3 | [13] |

## 验证

运行 `.venv/bin/python scripts/check_full_alignment.py`。来源变化、证据漏项、页码错误或遗漏discarded块都会让检查失败。

状态统计：{"MATCHED": 87, "WORDING_DIFFERENCE": 4, "CONFLICT": 2, "SHARED_BILINGUAL_SOURCE": 82, "CONTEXT_ONLY": 10}。
