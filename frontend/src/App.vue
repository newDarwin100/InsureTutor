<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { presentReply } from './api/presentation'
import { getStatus, askQuestion, type AppStatus, type ChatReply, type Language } from './api/client'

const status = ref<AppStatus | null>(null)
const error = ref('')
const input = ref('')
const busy = ref(false)
const page = ref(8)
const language = ref<Language>('zh-Hans')
const messages = ref<{ role: 'user' | 'assistant'; text: string; reply?: ChatReply }[]>([])
const messageArea = ref<HTMLElement | null>(null)
const displayMessages = computed(() => messages.value.map(message => ({
  ...message, presentation: message.reply ? presentReply(message.reply) : null,
})))

function revealSource(index: number, number: number) {
  const group = document.getElementById(`source-${index}-${number}`) as HTMLDetailsElement | null
  if (!group) return
  const sources = group.closest('.sources') as HTMLDetailsElement | null
  if (sources) sources.open = true
  group.open = true
  group.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
}

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
    const reply = await askQuestion(value, language.value)
    messages.value.push({ role: 'assistant', text: reply.message, reply })
  } catch (err) {
    input.value = value
    error.value = err instanceof Error ? err.message : '请求失败，请手动重试。'
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
      <span class="badge">开发预览 · 单轮问答</span>
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
            <div><dt>保险问答</dt><dd>{{ status?.rag_ready ? '单轮已就绪' : '未就绪' }}</dd></div>
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
          <p class="small-note">回答附带原文引用及实际页码。跳页取决于浏览器阅读器支持。</p>
        </section>
      </aside>

      <section class="chat-panel" aria-label="保险问答">
        <div class="chat-header"><div><h2>保险资料问答</h2><p>每次提问独立检索，暂不记住之前的对话</p></div><button class="text-button" :disabled="busy" @click="messages = []">清空</button></div>
        <div ref="messageArea" class="messages" aria-live="polite">
          <div v-if="!messages.length" class="empty-state"><span class="empty-icon">↗</span><h3>从一个条款问题开始</h3><p>例如：4% 的利率是保证的吗？定期提款有什么条件？</p><p class="small-note">仅依据这份产品资料回答；资料中的历史数字不代表当前利率。</p></div>
          <div v-for="(message, index) in displayMessages" :key="index" class="message" :class="message.role">
            <span class="message-label">{{ message.role === 'user' ? '你' : 'InsureTutor' }}</span>
            <div class="answer-bubble">
              <p v-if="message.text">{{ message.text }}</p>
              <template v-if="message.reply && message.presentation">
                <p v-for="(paragraph, ci) in message.presentation.paragraphs" :key="ci">{{ paragraph.text }}
                  <a v-for="number in paragraph.references" :key="number" class="citation-number" :href="`#source-${index}-${number}`" :aria-label="`查看引用 ${number}`" @click.prevent="revealSource(index, number)">[{{ number }}]</a>
                </p>
              </template>
            </div>
            <template v-if="message.reply && message.presentation">
              <details v-if="message.presentation.groups.length" class="sources">
                <summary>查看依据 · {{ message.presentation.groups.length }} 页</summary>
                <details v-for="group in message.presentation.groups" :id="`source-${index}-${group.number}`" :key="group.number" class="source-group">
                  <summary>[{{ group.number }}] 第 {{ group.page }} 页 · {{ group.sources.length }} 段原文</summary>
                  <div class="source-heading"><span>{{ group.documentName }}</span><a :href="group.url" target="_blank" rel="noopener noreferrer">打开 PDF 此页 ↗</a></div>
                  <p class="source-note">整理后的原文，保留资料原来的语言</p>
                  <blockquote v-for="source in group.sources" :key="source.evidence_id">{{ source.text }}</blockquote>
                </details>
              </details>
              <details class="metrics">
                <summary>耗时 {{ (message.reply.metrics.total_ms / 1000).toFixed(1) }} 秒 · 查看运行数据</summary>
                <p>Retrieval: {{ message.reply.metrics.retrieval_ms }} ms · LLM: {{ (message.reply.metrics.llm_ms / 1000).toFixed(2) }} s · Total: {{ (message.reply.metrics.total_ms / 1000).toFixed(2) }} s<br />Chunks: {{ message.reply.metrics.retrieved_chunks }} · LLM tokens: {{ message.reply.metrics.llm_input_tokens }} in / {{ message.reply.metrics.llm_output_tokens }} out · Embedding: {{ message.reply.metrics.embedding_input_tokens }}</p>
              </details>
            </template>
          </div>
          <p v-if="busy" class="small-note">正在检索资料、生成回答并检查依据…</p>
        </div>
        <form class="composer" @submit.prevent="send">
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <label class="sr-only" for="message">保险问题</label>
          <label class="language-label">回答语言 <select v-model="language" :disabled="busy"><option value="zh-Hans">简体中文</option><option value="zh-Hant">繁體中文</option><option value="en">English</option></select></label>
          <div class="input-row"><input id="message" v-model="input" maxlength="2000" placeholder="输入保险条款问题…" autocomplete="off" :disabled="busy" /><button type="submit" :disabled="busy || !input.trim()">{{ busy ? '回答中' : '发送' }}</button></div>
        </form>
      </section>
    </div>
  </main>
</template>
