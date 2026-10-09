<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import EvaluationPanel from './components/EvaluationPanel.vue'
import { copies } from './copy'
import { presentReply } from './api/presentation'
import { characterCount, revealBudget, revealParagraphs } from './api/reveal'
import { askQuestion, createConversation, createWorkspace, listConversations, getConversation, renameConversation, deleteConversation, ApiError, type ChatReply, type ConversationSummary, type EvaluationRow, type Language } from './api/client'

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
const workspaceToken = ref<string | null>(null)
const chats = ref<ConversationSummary[]>([])
const loadingHistory = ref(true)
const sidebarOpen = ref(false)
const editingTitle = ref(false)
const titleInput = ref('')
const deletingChat = ref(false)
const activeChat = computed(() => chats.value.find(chat => chat.token === conversationToken.value))
const orderedChats = computed(() => [...chats.value].sort((a, b) => b.updated - a.updated))
const drafts = new Map<string, string>()
const WORKSPACE_KEY = 'insuretutor.workspace.v1'
const SELECTED_KEY = 'insuretutor.selected-chat.v1'
type Message = { role: 'user' | 'assistant'; text: string; reply?: ChatReply; language?: Language; errorCode?: string; visibleCharacters?: number; revealing?: boolean }
const messages = ref<Message[]>([])
const messageArea = ref<HTMLElement | null>(null)
const composerInput = ref<HTMLTextAreaElement | null>(null)
const followLatest = ref(true)
let lastScrollTop = 0
const isRevealing = computed(() => messages.value.some(message => message.revealing))
const displayMessages = computed(() => messages.value.map(message => {
  const presentation = message.reply ? presentReply(message.reply) : null
  const budget = message.visibleCharacters ?? Infinity
  return { ...message,
    text: message.errorCode ? savedError(message.errorCode, message.language ?? language.value) : Array.from(message.text).slice(0, budget).join(''),
    presentation: presentation ? { ...presentation, paragraphs: revealParagraphs(presentation.paragraphs, budget - characterCount(message.text)) } : null,
  }
}))

async function scrollToLatest(force = false) {
  if (force) followLatest.value = true
  await nextTick()
  if (followLatest.value && activeView.value === 'chat' && messageArea.value) {
    messageArea.value.scrollTop = messageArea.value.scrollHeight
    lastScrollTop = Math.max(0, messageArea.value.scrollTop)
  }
}

function onMessageScroll() {
  const area = messageArea.value
  if (!area) return
  const top = Math.max(0, area.scrollTop)
  if (top < lastScrollTop - 1) followLatest.value = false
  else if (area.scrollHeight - top - area.clientHeight < 32) followLatest.value = true
  lastScrollTop = top
}

function resizeComposer() {
  const element = composerInput.value
  if (!element) return
  element.style.height = 'auto'
  element.style.height = `${Math.min(element.scrollHeight + 2, 120)}px`
}

function onComposerKey(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && event.keyCode !== 229) {
    event.preventDefault()
    void send()
  }
}

let finishReveal: (() => void) | undefined
function animateReply(message: Message) {
  const total = characterCount(message.text) + (message.reply?.claims.reduce((sum, claim) => sum + characterCount(claim.text), 0) ?? 0)
  if (!total || window.matchMedia('(prefers-reduced-motion: reduce)').matches || document.hidden) return Promise.resolve()
  message.visibleCharacters = 0
  message.revealing = true
  return new Promise<void>(resolve => {
    const started = performance.now()
    let frame = 0
    const finish = () => {
      cancelAnimationFrame(frame)
      document.removeEventListener('visibilitychange', onVisibility)
      message.visibleCharacters = total
      message.revealing = false
      finishReveal = undefined
      resolve()
    }
    const onVisibility = () => { if (document.hidden) finish() }
    const tick = (now: number) => {
      message.visibleCharacters = revealBudget(now - started, total)
      void scrollToLatest()
      if (message.visibleCharacters >= total) finish()
      else frame = requestAnimationFrame(tick)
    }
    finishReveal = finish
    document.addEventListener('visibilitychange', onVisibility)
    frame = requestAnimationFrame(tick)
  })
}
onBeforeUnmount(() => finishReveal?.())
watch(activeView, () => { void scrollToLatest() })
watch(input, () => { void nextTick(resizeComposer) })

function revealSource(index: number, number: number) {
  const group = document.getElementById(`source-${index}-${number}`) as HTMLDetailsElement | null
  if (!group) return
  followLatest.value = false
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

function savedError(code: string, lang: Language) {
  const copy = copies[lang]
  const errors: Record<string, string> = { MODEL_UNAVAILABLE: copy.modelError, RAG_UNAVAILABLE: copy.ragError,
    REQUEST_INTERRUPTED: copy.interrupted, REQUEST_FAILED: copy.requestError, pending: copy.pendingReply }
  return errors[code] ?? copy.requestError
}

async function refreshChats() {
  if (workspaceToken.value) chats.value = (await listConversations(workspaceToken.value)).conversations
}

async function selectChat(token: string) {
  if (busy.value) return
  loadingHistory.value = true
  error.value = ''
  try {
    const saved = await getConversation(token)
    if (conversationToken.value) drafts.set(conversationToken.value, input.value)
    localStorage.setItem(SELECTED_KEY, token)
    conversationToken.value = token
    messages.value = saved.messages.map(message => ({ role: message.role, text: message.text,
      reply: message.reply ?? undefined, language: message.language,
      errorCode: message.error_code ?? (message.status === 'pending' ? 'pending' : undefined) }))
    input.value = drafts.get(token) ?? ''
    activeView.value = 'chat'
    editingTitle.value = false
    deletingChat.value = false
    sidebarOpen.value = false
    await scrollToLatest(true)
  } catch (err) { error.value = localizedError(err, t.value.historyError) }
  finally { loadingHistory.value = false }
}

async function newChat() {
  if (busy.value || !workspaceToken.value) return
  loadingHistory.value = true
  error.value = ''
  try {
    const created = await createConversation(workspaceToken.value)
    await refreshChats()
    await selectChat(created.token)
  } catch (err) { error.value = localizedError(err, t.value.historyError) }
  finally { loadingHistory.value = false }
}

onMounted(async () => {
  try {
    workspaceToken.value = localStorage.getItem(WORKSPACE_KEY)
    if (workspaceToken.value) {
      try { await refreshChats() }
      catch (err) {
        if (!(err instanceof ApiError) || err.code !== 'WORKSPACE_EXPIRED') throw err
        workspaceToken.value = null
      }
    }
    if (!workspaceToken.value) {
      workspaceToken.value = (await createWorkspace()).token
      localStorage.setItem(WORKSPACE_KEY, workspaceToken.value)
      await refreshChats()
    }
    const previous = localStorage.getItem(SELECTED_KEY)
    const selected = chats.value.find(chat => chat.token === previous) ?? orderedChats.value[0]
    if (selected) await selectChat(selected.token)
    else await newChat()
  } catch (err) {
    error.value = err instanceof DOMException ? t.value.storageError : localizedError(err, t.value.historyError)
  } finally { loadingHistory.value = false }
})

function editTitle() { titleInput.value = activeChat.value?.title ?? ''; editingTitle.value = true }
async function saveTitle() {
  if (!conversationToken.value || !titleInput.value.trim()) return
  loadingHistory.value = true
  try { await renameConversation(conversationToken.value, titleInput.value.trim()); await refreshChats(); editingTitle.value = false }
  catch (err) { error.value = localizedError(err, t.value.historyError) }
  finally { loadingHistory.value = false }
}

async function removeChat() {
  if (busy.value || !conversationToken.value) return
  loadingHistory.value = true
  try {
    const removed = conversationToken.value
    await deleteConversation(removed)
    drafts.delete(removed)
    conversationToken.value = null
    messages.value = []
    input.value = ''
    deletingChat.value = false
    await refreshChats()
    if (orderedChats.value[0]) await selectChat(orderedChats.value[0].token)
    else await newChat()
  } catch (err) { error.value = localizedError(err, t.value.historyError) }
  finally { loadingHistory.value = false }
}

async function send() {
  const value = input.value.trim()
  if (!value || busy.value || loadingHistory.value || !conversationToken.value) return
  busy.value = true
  error.value = ''
  messages.value.push({ role: 'user', text: value })
  input.value = ''
  await scrollToLatest(true)
  try {
    if (activeChat.value) {
      if (!activeChat.value.title) activeChat.value.title = value.replace(/\s+/g, ' ').slice(0, 42)
      activeChat.value.updated = Date.now() / 1000
    }
    const reply = await askQuestion(value, 'auto', conversationToken.value)
    messages.value.push({ role: 'assistant', text: reply.message, reply, language: reply.language })
    const message = messages.value[messages.value.length - 1]!
    runs.value.push({ id: reply.request_id ?? `live-${Date.now()}-${runs.value.length}`, group: 'live',
      source: 'live', kind: 'answer', provenance: 'real', question: value, language: reply.language ?? null,
      status: reply.action, measured_at: new Date().toISOString(), model: null,
      retrieval_ms: reply.metrics.retrieval_ms, llm_ms: reply.metrics.llm_ms, total_ms: reply.metrics.total_ms,
      chunks: reply.metrics.retrieved_chunks, embedding_input_tokens: reply.metrics.embedding_input_tokens,
      llm_input_tokens: reply.metrics.llm_input_tokens, llm_output_tokens: reply.metrics.llm_output_tokens,
      direct_recall: null, expanded_coverage: null, query_cached: false })
    if (runs.value.length > 200) runs.value.shift()
    await animateReply(message)
  } catch (err) {
    input.value = value
    error.value = localizedError(err, t.value.requestError)
    messages.value.push({ role: 'assistant', text: '', errorCode: err instanceof ApiError ? err.code : 'REQUEST_FAILED', language: activeChat.value?.language })
  } finally {
    try { await refreshChats() } catch { error.value = error.value || t.value.historyError }
    busy.value = false
    await scrollToLatest()
    if (activeView.value === 'chat') composerInput.value?.focus({ preventScroll: true })
  }
}

function documentUrl() {
  const selected = Number.isFinite(page.value) ? Math.min(20, Math.max(1, Math.trunc(page.value))) : 1
  return `/api/documents/flexi-ulife-prime-saver#page=${selected}`
}

</script>

<template>
  <main class="app-shell" :class="{ 'chat-mode': activeView === 'chat' }">
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
    <div id="chat-view" v-show="activeView === 'chat'" class="chat-workspace" :class="{ 'sidebar-open': sidebarOpen }" role="tabpanel" aria-labelledby="chat-tab">
      <button v-if="sidebarOpen" class="sidebar-backdrop" :aria-label="t.closeHistory" @click="sidebarOpen = false"></button>
      <aside class="chat-sidebar" :aria-label="t.chatHistory">
        <div class="history-heading"><h2>{{ t.chatHistory }}</h2><button class="mobile-close text-button" :aria-label="t.closeHistory" @click="sidebarOpen = false">×</button></div>
        <button class="new-chat-button" :disabled="busy || loadingHistory || !workspaceToken" @click="newChat">＋ {{ t.newChat }}</button>
        <div class="chat-list">
          <button v-for="chat in orderedChats" :key="chat.token" class="chat-list-item" :class="{ selected: chat.token === conversationToken }" :aria-current="chat.token === conversationToken ? 'page' : undefined" :disabled="busy || loadingHistory" :title="chat.title || t.newChat" @click="selectChat(chat.token)"><span>{{ chat.title || t.newChat }}</span><small>{{ new Date(chat.updated * 1000).toLocaleDateString(language === 'en' ? 'en-US' : language === 'zh-Hant' ? 'zh-TW' : 'zh-CN', { month: 'short', day: 'numeric' }) }}</small></button>
        </div>
        <p class="history-note">{{ t.historyNoteShort }}</p>
      </aside>
      <div class="chat-content">
      <section class="source-strip">
        <div><span class="eyebrow">{{ t.knowledge }}</span><h2>FLEXI-ULife Prime Saver <small>PDF · 20 {{ t.pages }}</small></h2></div>
        <div class="source-actions"><label class="sr-only" for="pdf-page">{{ t.pdfPage }}</label><span>{{ t.page }}</span><input id="pdf-page" v-model.number="page" type="number" min="1" max="20" step="1"/><a class="document-link" :href="documentUrl()" target="_blank" rel="noopener noreferrer">{{ t.openPdf }}</a></div>
      </section>
      <section class="chat-panel" :aria-label="t.tutor">
        <div class="chat-header"><button class="history-toggle text-button" :aria-label="t.chatHistory" :aria-expanded="sidebarOpen" @click="sidebarOpen = !sidebarOpen">☰</button><div class="chat-heading"><h2 :title="activeChat?.title">{{ activeChat?.title || t.chatTitle }}</h2><p>{{ t.memory }}</p></div><div class="chat-actions"><button class="text-button" :disabled="busy || loadingHistory || !conversationToken" @click="editTitle">{{ t.rename }}</button><button class="text-button" :disabled="busy || loadingHistory || !conversationToken" @click="deletingChat = true">{{ t.deleteChat }}</button></div></div>
        <form v-if="editingTitle" class="chat-edit-bar" @submit.prevent="saveTitle"><label class="sr-only" for="chat-title">{{ t.rename }}</label><input id="chat-title" v-model="titleInput" maxlength="80" :placeholder="t.chatTitle" :disabled="loadingHistory" /><button type="submit" :disabled="loadingHistory || !titleInput.trim()">{{ t.save }}</button><button type="button" :disabled="loadingHistory" @click="editingTitle = false">{{ t.cancel }}</button></form>
        <div v-if="deletingChat" class="chat-edit-bar delete-confirm" role="alert"><span>{{ t.deleteConfirm }}</span><button :disabled="loadingHistory" @click="removeChat">{{ t.deleteChat }}</button><button :disabled="loadingHistory" @click="deletingChat = false">{{ t.cancel }}</button></div>
        <div class="message-window">
        <div ref="messageArea" class="messages" role="log" aria-live="polite" :aria-busy="busy" @scroll="onMessageScroll" @wheel="event => { if (event.deltaY < 0) followLatest = false }">
          <div v-if="!messages.length" class="empty-state"><span class="empty-icon">↗</span><h3>{{ loadingHistory ? t.loadingHistory : t.start }}</h3><p>{{ t.example }}</p><p class="small-note">{{ t.historical }}</p></div>
          <div v-for="(message, index) in displayMessages" :key="index" class="message" :class="message.role">
            <span class="message-label">{{ message.role === 'user' ? t.you : 'InsureTutor' }}</span>
            <div class="answer-bubble" :class="{ revealing: message.revealing }">
              <p v-if="message.text">{{ message.text }}</p>
              <template v-if="message.reply && message.presentation">
                <p v-for="(paragraph, ci) in message.presentation.paragraphs" :key="ci">{{ paragraph.text }}
                  <a v-for="number in message.revealing ? [] : paragraph.references" :key="number" class="citation-number" :href="`#source-${index}-${number}`" :aria-label="`${t.viewCitation} ${number}`" @click.prevent="revealSource(index, number)">[{{ number }}]</a>
                </p>
              </template>
              <span v-if="message.revealing && !message.text && !message.presentation?.paragraphs.length" class="typing-cursor" aria-hidden="true">▍</span>
            </div>
            <template v-if="message.reply && message.presentation && !message.revealing">
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
          <div v-if="busy && !isRevealing" class="waiting-status" role="status"><span class="waiting-dots" aria-hidden="true"><i></i><i></i><i></i></span>{{ t.waiting }}</div>
        </div>
        <button v-if="!followLatest && messages.length" class="jump-latest" type="button" @click="scrollToLatest(true)">↓ {{ t.latest }}</button>
        </div>
        <form class="composer" @submit.prevent="send">
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <label class="sr-only" for="message">{{ t.question }}</label>
          <div class="input-row"><textarea id="message" ref="composerInput" v-model="input" rows="1" maxlength="2000" :placeholder="t.placeholder" :aria-describedby="'composer-hint'" :disabled="busy || loadingHistory || !conversationToken" @keydown="onComposerKey" /><button type="submit" :disabled="busy || loadingHistory || !conversationToken || !input.trim()">{{ busy ? t.answering : t.send }}</button></div>
          <p id="composer-hint" class="composer-hint">{{ t.composerHint }}</p>
        </form>
      </section>
      </div>
    </div>
    <EvaluationPanel id="performance-view" v-show="activeView === 'performance'" role="tabpanel" aria-labelledby="performance-tab" :language="language" :runs="runs" />
  </main>
</template>
