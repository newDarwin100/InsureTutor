<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import EvaluationPanel from './components/EvaluationPanel.vue'
import { copies } from './copy'
import { presentReply } from './api/presentation'
import { askQuestion, createConversation, deleteConversation, ApiError, type ChatReply, type EvaluationRow, type Language } from './api/client'

const activeView = ref('chat')
const runs = ref<EvaluationRow[]>([])
const error = ref('')
const input = ref('')
const busy = ref(false)
const page = ref(8)
const language = ref<Language>('zh-Hans')
const t = computed(() => copies[language.value])
watch(language, (value, previous) => {
  document.documentElement.lang = value
  if (previous && error.value) {
    const key = (Object.keys(copies[previous]) as (keyof typeof t.value)[]).find(k => copies[previous][k] === error.value)
    if (key) error.value = copies[value][key]
  }
}, { immediate: true })
const conversationToken = ref<string | null>(null)
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

function localizedError(err: unknown, fallback: string) {
  if (err instanceof ApiError) {
    const messages: Record<string, string> = {
      CONVERSATION_EXPIRED: t.value.expired, CONVERSATION_BUSY: t.value.busy,
      CONVERSATION_LIMIT: t.value.limit, MODEL_UNAVAILABLE: t.value.modelError, RAG_UNAVAILABLE: t.value.ragError,
    }
    return messages[err.code] ?? fallback
  }
  return fallback
}

async function send() {
  const value = input.value.trim()
  if (!value || busy.value) return
  busy.value = true
  error.value = ''
  messages.value.push({ role: 'user', text: value })
  input.value = ''
  try {
    if (!conversationToken.value) conversationToken.value = (await createConversation()).token
    const reply = await askQuestion(value, language.value, conversationToken.value)
    messages.value.push({ role: 'assistant', text: reply.message, reply })
    runs.value.push({ id: reply.request_id ?? `live-${Date.now()}-${runs.value.length}`, group: 'live',
      source: 'live', kind: 'answer', provenance: 'real', question: value, language: language.value,
      status: reply.action, measured_at: new Date().toISOString(), model: null,
      retrieval_ms: reply.metrics.retrieval_ms, llm_ms: reply.metrics.llm_ms, total_ms: reply.metrics.total_ms,
      chunks: reply.metrics.retrieved_chunks, embedding_input_tokens: reply.metrics.embedding_input_tokens,
      llm_input_tokens: reply.metrics.llm_input_tokens, llm_output_tokens: reply.metrics.llm_output_tokens,
      direct_recall: null, expanded_coverage: null, query_cached: false })
    if (runs.value.length > 200) runs.value.shift()
  } catch (err) {
    input.value = value
    error.value = localizedError(err, t.value.requestError)
  } finally {
    busy.value = false
    await nextTick()
    messageArea.value?.scrollTo({ top: messageArea.value.scrollHeight, behavior: 'smooth' })
  }
}

async function clearChat() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    if (conversationToken.value) await deleteConversation(conversationToken.value)
    conversationToken.value = null
    messages.value = []
  } catch (err) {
    error.value = localizedError(err, t.value.clearError)
  } finally { busy.value = false }
}

function documentUrl() {
  const selected = Number.isFinite(page.value) ? Math.min(20, Math.max(1, Math.trunc(page.value))) : 1
  return `/api/documents/flexi-ulife-prime-saver#page=${selected}`
}

</script>

<template>
  <main class="app-shell">
    <header class="header">
      <div class="brand"><span class="brand-icon">IT</span><div><h1>InsureTutor</h1><p>{{ t.tagline }}</p></div></div>
      <span class="badge">{{ t.preview }}</span>
    </header>

    <div class="workspace-nav">
      <div class="view-tabs" role="tablist" :aria-label="t.tutor">
        <button id="chat-tab" role="tab" :aria-selected="activeView === 'chat'" aria-controls="chat-view" :class="{ active: activeView === 'chat' }" @click="activeView = 'chat'">{{ t.conversation }}</button>
        <button id="performance-tab" role="tab" :aria-selected="activeView === 'performance'" aria-controls="performance-view" :class="{ active: activeView === 'performance' }" @click="activeView = 'performance'">{{ t.performance }}<span v-if="runs.length" class="tab-count">{{ runs.length }}</span></button>
      </div>
      <label class="language-label">{{ t.language }} <select v-model="language" :disabled="busy"><option value="zh-Hans">简体中文</option><option value="zh-Hant">繁體中文</option><option value="en">English</option></select></label>
    </div>
    <div id="chat-view" v-show="activeView === 'chat'" role="tabpanel" aria-labelledby="chat-tab">
      <section class="source-strip">
        <div><span class="eyebrow">{{ t.knowledge }}</span><h2>FLEXI-ULife Prime Saver <small>PDF · 20 {{ t.pages }}</small></h2></div>
        <div class="source-actions"><label class="sr-only" for="pdf-page">{{ t.pdfPage }}</label><span>{{ t.page }}</span><input id="pdf-page" v-model.number="page" type="number" min="1" max="20" step="1"/><a class="document-link" :href="documentUrl()" target="_blank" rel="noopener noreferrer">{{ t.openPdf }}</a></div>
      </section>
      <section class="chat-panel" :aria-label="t.tutor">
        <div class="chat-header"><div><h2>{{ t.chatTitle }}</h2><p>{{ t.memory }}</p></div><button class="text-button" :disabled="busy" @click="clearChat">{{ t.clear }}</button></div>
        <div ref="messageArea" class="messages" aria-live="polite">
          <div v-if="!messages.length" class="empty-state"><span class="empty-icon">↗</span><h3>{{ t.start }}</h3><p>{{ t.example }}</p><p class="small-note">{{ t.historical }}</p></div>
          <div v-for="(message, index) in displayMessages" :key="index" class="message" :class="message.role">
            <span class="message-label">{{ message.role === 'user' ? t.you : 'InsureTutor' }}</span>
            <div class="answer-bubble">
              <p v-if="message.text">{{ message.text }}</p>
              <template v-if="message.reply && message.presentation">
                <p v-for="(paragraph, ci) in message.presentation.paragraphs" :key="ci">{{ paragraph.text }}
                  <a v-for="number in paragraph.references" :key="number" class="citation-number" :href="`#source-${index}-${number}`" :aria-label="`${t.viewCitation} ${number}`" @click.prevent="revealSource(index, number)">[{{ number }}]</a>
                </p>
              </template>
            </div>
            <template v-if="message.reply && message.presentation">
              <details v-if="message.reply.verification?.status === 'failed'" class="metrics">
                <summary>{{ t.failure }}</summary>
                <p v-if="message.reply.verification.detail">{{ t.auditNote }}: {{ message.reply.verification.detail }}</p>
                <p>{{ t.classification }}: {{ message.reply.verification.reason }} · {{ t.request }}: {{ message.reply.request_id?.slice(0, 8) }}</p>
              </details>
              <details v-if="message.presentation.groups.length" class="sources">
                <summary>{{ t.sources }} · {{ message.presentation.groups.length }} {{ t.pages }}</summary>
                <details v-for="group in message.presentation.groups" :id="`source-${index}-${group.number}`" :key="group.number" class="source-group">
                  <summary>[{{ group.number }}] {{ t.page }} {{ group.page }} · {{ group.sources.length }} {{ t.passages }}</summary>
                  <div class="source-heading"><span>{{ group.documentName }}</span><a :href="group.url" target="_blank" rel="noopener noreferrer">{{ t.openPage }}</a></div>
                  <p class="source-note">{{ t.originalNote }}</p>
                  <blockquote v-for="source in group.sources" :key="source.evidence_id">{{ source.text }}</blockquote>
                </details>
              </details>
              <details class="metrics">
                <summary>{{ t.elapsed }} {{ (message.reply.metrics.total_ms / 1000).toFixed(1) }} {{ t.seconds }} · {{ t.runtime }}</summary>
                <p>{{ t.retrieval }}: {{ message.reply.metrics.retrieval_ms }} ms · {{ t.llm }}: {{ (message.reply.metrics.llm_ms / 1000).toFixed(2) }} s · {{ t.total }}: {{ (message.reply.metrics.total_ms / 1000).toFixed(2) }} s<br />{{ t.chunks }}: {{ message.reply.metrics.retrieved_chunks }} · {{ t.inputTokens }}: {{ message.reply.metrics.llm_input_tokens }} / {{ t.outputTokens }}: {{ message.reply.metrics.llm_output_tokens }} · {{ t.embedding }}: {{ message.reply.metrics.embedding_input_tokens }}</p>
              </details>
            </template>
          </div>
          <p v-if="busy" class="small-note">{{ t.waiting }}</p>
        </div>
        <form class="composer" @submit.prevent="send">
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <label class="sr-only" for="message">{{ t.question }}</label>
          <div class="input-row"><input id="message" v-model="input" maxlength="2000" :placeholder="t.placeholder" autocomplete="off" :disabled="busy" /><button type="submit" :disabled="busy || !input.trim()">{{ busy ? t.answering : t.send }}</button></div>
        </form>
      </section>
    </div>
    <EvaluationPanel id="performance-view" v-show="activeView === 'performance'" role="tabpanel" aria-labelledby="performance-tab" :language="language" :runs="runs" />
  </main>
</template>
