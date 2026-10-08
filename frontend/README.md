# 前端

Vue 3 + Vite + TypeScript + 普通 CSS。

- `src/App.vue`：会话、语言切换、引用、错误处理和计时。
- `src/copy.ts`：英文、简体和繁体界面文案。
- `src/components/EvaluationPanel.vue`：只读历史评测看板。
- `src/api/`：请求和类型；API key 不进入前端。

在本目录执行 `npm ci`、`npm test`、`npm run build`。
从根目录运行 `bash scripts/dev.sh` 同时启动前后端，开发代理指向后端。
Docker 编译前端后由 FastAPI 提供页面。完整说明见 [README](../README.md)。
