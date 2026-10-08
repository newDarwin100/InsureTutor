# 前端

Vue 3 + Vite + TypeScript + 普通 CSS，单页聊天。

- src/components/：聊天、语言选择、引用卡片与评测视图。
- src/api/：后端请求和响应类型。

已有最小页面：连接测试、后端/资料状态、指定页码的 PDF 链接。API key 只由后端读取。保险问答和三语言 UI 尚未接入。

在本目录执行 npm ci；npm run dev 启动开发服务，npm run build 做类型检查与构建。建议从项目根目录运行 bash scripts/dev.sh 同时启动后端。依赖版本由 package-lock.json 锁定。
