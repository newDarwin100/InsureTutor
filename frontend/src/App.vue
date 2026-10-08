<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { getStatus, testConnection, type AppStatus } from './api/client'

const status = ref<AppStatus | null>(null)
const error = ref('')
const input = ref('')
const busy = ref(false)
const page = ref(8)
const messages = ref<{ role: 'user' | 'assistant'; text: string }[]>([])
const messageArea = ref<HTMLElement | null>(null)

async function refresh() {
  error.value = ''
  try { status.value = await getStatus() }
  catch { error.value = '后端暂时无法连接，请确认启动脚本正在运行。' }
}

async function send() {
  const value = input.value.trim()
  if (!value || busy.value) return
  busy.value = true
  error.value = ''
  messages.value.push({ role: 'user', text: value })
  input.value = ''
  try {
    const reply = await testConnection(value)
    messages.value.push({ role: 'assistant', text: reply.message })
  } catch {
    input.value = value
    error.value = '连接测试失败。可重试，当前没有调用模型。'
  } finally {
    busy.value = false
    await nextTick()
    messageArea.value?.scrollTo({ top: messageArea.value.scrollHeight, behavior: 'smooth' })
  }
}

function documentUrl() {
  const selected = Number.isFinite(page.value) ? Math.min(20, Math.max(1, Math.trunc(page.value))) : 1
  return `/api/documents/flexi-ulife-prime-saver#page=${selected}`
}

onMounted(refresh)
</script>

<template>
  <main class="app-shell">
    <header class="header">
      <div class="brand"><span class="brand-icon">IT</span><div><h1>InsureTutor</h1><p>读懂条款，找到依据</p></div></div>
      <span class="badge">开发预览 · 连接测试</span>
    </header>

    <div class="layout">
      <aside class="sidebar">
        <section class="panel">
          <h2>项目状态</h2>
          <dl>
            <div><dt>后端</dt><dd>{{ status ? '已连接' : '未连接' }}</dd></div>
            <div><dt>资料</dt><dd>{{ status?.document_available ? 'PDF 已就绪' : '检查中' }}</dd></div>
            <div><dt>来源证据</dt><dd>{{ status?.knowledge_counts.evidence ?? '—' }}</dd></div>
            <div><dt>检索分块</dt><dd>{{ status?.knowledge_counts.chunks ?? '—' }}</dd></div>
            <div><dt>保险问答</dt><dd>尚未接入</dd></div>
          </dl>
          <button class="text-button" @click="refresh">刷新状态</button>
        </section>
        <section class="panel document-panel">
          <span class="eyebrow">知识来源</span>
          <h2>FLEXI-ULife<br />Prime Saver</h2>
          <p>原始保险文件 · 20 页</p>
          <label for="pdf-page">PDF 实际页码（包含封面）</label>
          <input id="pdf-page" v-model.number="page" type="number" min="1" max="20" step="1" />
          <a class="document-link" :href="documentUrl()" target="_blank" rel="noopener noreferrer">打开 PDF ↗</a>
          <p class="small-note">这是文档跳转入口。回答中的引用将随 RAG 接入；跳页取决于浏览器阅读器支持。</p>
        </section>
      </aside>

      <section class="chat-panel" aria-label="连接测试">
        <div class="chat-header"><div><h2>连接测试</h2><p>先验证前后端与原文件访问</p></div><button class="text-button" :disabled="busy" @click="messages = []">清空</button></div>
        <div ref="messageArea" class="messages" aria-live="polite">
          <div v-if="!messages.length" class="empty-state"><span class="empty-icon">↗</span><h3>项目的第一条链路已准备好</h3><p>发送一条消息测试连接，也可以从左侧打开指定 PDF 页面。</p><p class="small-note">当前不会回答保险问题，不调用模型或检索。</p></div>
          <div v-for="(message, index) in messages" :key="index" class="message" :class="message.role"><span class="message-label">{{ message.role === 'user' ? '你' : 'InsureTutor' }}</span><p>{{ message.text }}</p></div>
          <p v-if="busy" class="small-note">正在连接后端…</p>
        </div>
        <form class="composer" @submit.prevent="send">
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <label class="sr-only" for="message">连接测试消息</label>
          <div class="input-row"><input id="message" v-model="input" maxlength="2000" placeholder="输入一条测试消息…" autocomplete="off" :disabled="busy" /><button type="submit" :disabled="busy || !input.trim()">{{ busy ? '连接中' : '测试连接' }}</button></div>
        </form>
      </section>
    </div>
  </main>
</template>
