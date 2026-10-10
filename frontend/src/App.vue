<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import EvaluationPanel from './components/EvaluationPanel.vue'
import Icon from './components/Icon.vue'
import { copies } from './copy'
import { presentReply } from './api/presentation'
import { streamQuestion, createConversation, createWorkspace, listConversations, getConversation, renameConversation, deleteConversation, ApiError, type ChatReply, type ConversationSummary, type EvaluationRow, type Language } from './api/client'

const activeView = ref('chat')
const runs = ref<EvaluationRow[]>([])
const error = ref('')
const input = ref('')
const busy = ref(false)
const page = ref(8)
const language = ref<Language>('zh-Hans')
const t = computed(() => copies[language.value])
const prompts = computed(() => [
  { icon: 'shield', title: t.value.rateTopic, text: t.value.rateExample, question: t.value.rateQuestion },
  { icon: 'wallet', title: t.value.withdrawTopic, text: t.value.withdrawExample, question: t.value.withdrawQuestion },
  { icon: 'clock', title: t.value.unemploymentTopic, text: t.value.unemploymentExample, question: t.value.unemploymentQuestion },
])
async function choosePrompt(question: string) { input.value = question; await nextTick(); composerInput.value?.focus({ preventScroll: true }) }
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
type Message = { role: 'user' | 'assistant'; text: string; reply?: ChatReply; language?: Language; errorCode?: string; pending?: boolean; visibleChars?: number }
const messages = ref<Message[]>([])
const messageArea = ref<HTMLElement | null>(null)
const composerInput = ref<HTMLTextAreaElement | null>(null)
const followLatest = ref(true)
const streamStage = ref('retrieval')
const awaitingReply = computed(() => messages.value.some(message => message.pending))
const streamLabel = computed(() => streamStage.value === 'verification' ? t.value.streamChecking :
  streamStage.value === 'resolution' ? t.value.resolving : streamStage.value === 'retrieval' ? t.value.retrieving : t.value.streaming)
let activeStream: AbortController | undefined
let finishReveal: (() => void) | undefined
onBeforeUnmount(() => { activeStream?.abort(); finishReveal?.() })
const displayMessages = computed(() => messages.value.map(message => {
  const presentation = message.reply ? presentReply(message.reply) : null
  let remaining = message.visibleChars ?? Infinity
  const text = message.errorCode ? savedError(message.errorCode, message.language ?? language.value) : message.text
  const shownText = Array.from(text).slice(0, remaining).join('')
  remaining = Math.max(0, remaining - Array.from(text).length)
  if (presentation) presentation.paragraphs = presentation.paragraphs.map(paragraph => {
    const length = Array.from(paragraph.text).length
    const shown = { text: Array.from(paragraph.text).slice(0, remaining).join(''),
      references: remaining >= length ? paragraph.references : [] }
    remaining = Math.max(0, remaining - length)
    return shown
  }).filter(paragraph => paragraph.text)
  return { ...message, text: shownText, presentation }
}))

// This animation reveals only an already checked reply, never a model draft.
async function revealFinal(message: Message) {
  const length = Array.from(message.text).length + (message.reply?.claims.reduce((sum, claim) => sum + Array.from(claim.text).length, 0) ?? 0)
  if (!message.reply?.claims.length || document.hidden || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  message.visibleChars = 1
  await scrollToLatest()
  await new Promise<void>(resolve => {
    const began = performance.now()
    const duration = Math.min(1200, length * 6)
    let frame = 0
    const finish = () => {
      cancelAnimationFrame(frame)
      delete message.visibleChars
      document.removeEventListener('visibilitychange', hidden)
      finishReveal = undefined
      resolve()
    }
    const hidden = () => { if (document.hidden) finish() }
    const tick = (now: number) => {
      message.visibleChars = Math.max(1, Math.ceil(length * Math.min(1, (now - began) / duration)))
      void scrollToLatest()
      if (now - began >= duration) finish()
      else frame = requestAnimationFrame(tick)
    }
    finishReveal = finish
    document.addEventListener('visibilitychange', hidden)
    frame = requestAnimationFrame(tick)
  })
}

async function scrollToLatest(force = false) {
  if (force) followLatest.value = true
  await nextTick()
  if (followLatest.value && activeView.value === 'chat' && messageArea.value) {
    messageArea.value.scrollTop = messages.value.length ? messageArea.value.scrollHeight : 0
  }
}

function onMessageScroll() {
  const area = messageArea.value
  if (!area) return
  if (area.scrollHeight - Math.max(0, area.scrollTop) - area.clientHeight < 32) followLatest.value = true
}

function onScrollPointer(event: PointerEvent) {
  const area = messageArea.value
  if (area && event.clientX >= area.getBoundingClientRect().right - 18) followLatest.value = false
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

function recordRun(reply: ChatReply, question: string, id: string, source: string, measuredAt: string) {
  if (runs.value.some(row => row.id === id)) return
  runs.value.push({ id, group: 'live', source, kind: 'answer', provenance: 'real', question,
    language: reply.language ?? null, status: reply.action, measured_at: measuredAt, model: null,
    retrieval_ms: reply.metrics.retrieval_ms, llm_ms: reply.metrics.llm_ms, total_ms: reply.metrics.total_ms,
    chunks: reply.metrics.retrieved_chunks, embedding_input_tokens: reply.metrics.embedding_input_tokens,
    llm_input_tokens: reply.metrics.llm_input_tokens, llm_output_tokens: reply.metrics.llm_output_tokens,
    direct_recall: null, expanded_coverage: null, query_cached: reply.metrics.query_cached ?? false,
    ttft_ms: reply.metrics.client_ttft_ms ?? reply.metrics.ttft_ms ?? null,
    generation_ms: reply.metrics.generation_ms ?? null, verification_ms: reply.metrics.verification_ms ?? null,
    question_resolution_ms: reply.metrics.question_resolution_ms ?? null })
  if (runs.value.length > 200) runs.value.splice(0, runs.value.length - 200)
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
    let question = ''
    saved.messages.forEach((message, index) => {
      if (message.role === 'user') question = message.text
      else if (message.reply) recordRun(message.reply, question, message.reply.request_id ?? `${token}-${index}`,
        'saved_chat', new Date(message.created * 1000).toISOString())
    })
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
  const requestStarted = performance.now()
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
    messages.value.push({ role: 'assistant', text: '', pending: true })
    const message = messages.value[messages.value.length - 1]!
    let firstText: number | null = null
    streamStage.value = 'retrieval'
    activeStream = new AbortController()
    const signal = AbortSignal.any([activeStream.signal, AbortSignal.timeout(180000)])
    const reply = await streamQuestion(value, conversationToken.value, (event, data) => {
      if (event === 'meta') message.language = data.language
      if (event === 'status') streamStage.value = data.stage
      // Ignore draft events even if connected to an older backend.
      if (event === 'done' && data.claims?.some((claim: { text: string }) => claim.text.trim()))
        firstText = performance.now() - requestStarted
    }, signal)
    reply.metrics.client_ttft_ms = firstText
    message.text = reply.message
    message.reply = reply
    message.language = reply.language
    message.pending = false
    await revealFinal(message)
    recordRun(reply, value, reply.request_id ?? `live-${Date.now()}-${runs.value.length}`, 'live', new Date().toISOString())
  } catch (err) {
    input.value = value
    error.value = localizedError(err, t.value.requestError)
    const message = messages.value[messages.value.length - 1]
    const failed = { role: 'assistant' as const, text: '', errorCode: err instanceof ApiError ? err.code : 'REQUEST_FAILED', language: message?.language ?? activeChat.value?.language }
    if (message?.role === 'assistant' && message.pending) messages.value[messages.value.length - 1] = failed
    else messages.value.push(failed)
  } finally {
    activeStream = undefined
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
      <div class="brand"><span class="brand-icon"><Icon name="book" /></span><div><h1>InsureTutor</h1><p>{{ t.tagline }}</p></div></div>
      <div class="workspace-nav">
      <div class="view-tabs" role="tablist" :aria-label="t.tutor">
        <button id="chat-tab" role="tab" :aria-selected="activeView === 'chat'" aria-controls="chat-view" :class="{ active: activeView === 'chat' }" @click="activeView = 'chat'"><Icon name="chat" />{{ t.conversation }}</button>
        <button id="performance-tab" role="tab" :aria-selected="activeView === 'performance'" aria-controls="performance-view" :class="{ active: activeView === 'performance' }" @click="activeView = 'performance'"><Icon name="chart" />{{ t.performance }}<span v-if="runs.length" class="tab-count">{{ runs.length }}</span></button>
      </div>
      <label class="language-label"><Icon name="globe" /><span class="sr-only">{{ t.language }}</span><select v-model="language" :disabled="busy"><option value="zh-Hans">简体中文</option><option value="zh-Hant">繁體中文</option><option value="en">English</option></select></label>
      </div>
    </header>
    <div id="chat-view" v-show="activeView === 'chat'" class="chat-workspace" :class="{ 'sidebar-open': sidebarOpen }" role="tabpanel" aria-labelledby="chat-tab">
      <button v-if="sidebarOpen" class="sidebar-backdrop" :aria-label="t.closeHistory" @click="sidebarOpen = false"></button>
      <aside class="chat-sidebar" :aria-label="t.chatHistory">
        <button class="new-chat-button" :disabled="busy || loadingHistory || !workspaceToken" @click="newChat"><Icon name="plus" />{{ t.newChat }}<span aria-hidden="true">↗</span></button>
        <div class="history-heading"><h2>{{ t.chatHistory }}</h2><button class="mobile-close icon-button" :aria-label="t.closeHistory" @click="sidebarOpen = false"><Icon name="close" /></button></div>
        <div class="chat-list">
          <button v-for="chat in orderedChats" :key="chat.token" class="chat-list-item" :class="{ selected: chat.token === conversationToken }" :aria-current="chat.token === conversationToken ? 'page' : undefined" :disabled="busy || loadingHistory" :title="chat.title || t.newChat" @click="selectChat(chat.token)"><span>{{ chat.title || t.newChat }}</span><small>{{ new Date(chat.updated * 1000).toLocaleDateString(language === 'en' ? 'en-US' : language === 'zh-Hant' ? 'zh-TW' : 'zh-CN', { month: 'short', day: 'numeric' }) }}</small></button>
        </div>
        <div class="history-footer"><span class="footer-avatar"><Icon name="shield" /></span><div><strong>InsureTutor</strong><p>{{ t.historyNoteShort }}</p></div></div>
      </aside>
      <div class="chat-content">
      <section class="chat-panel" :aria-label="t.tutor">
        <div class="chat-header"><button class="history-toggle icon-button" :aria-label="t.chatHistory" :aria-expanded="sidebarOpen" @click="sidebarOpen = !sidebarOpen"><Icon name="menu" /></button><div class="chat-heading"><span class="eyebrow">{{ t.tutor }}</span><h2 :title="activeChat?.title">{{ activeChat?.title || t.newChat }}</h2></div><div class="chat-actions"><button class="icon-button" :title="t.rename" :aria-label="t.rename" :disabled="busy || loadingHistory || !conversationToken" @click="editTitle"><Icon name="edit" /></button><button class="icon-button danger-button" :title="t.deleteChat" :aria-label="t.deleteChat" :disabled="busy || loadingHistory || !conversationToken" @click="deletingChat = true"><Icon name="trash" /></button></div></div>
      <section class="source-strip">
        <div class="document-name"><Icon name="file" /><span>FLEXI-ULife Prime Saver <small>20 {{ t.pages }}</small></span></div>
        <div class="source-actions"><label class="sr-only" for="pdf-page">{{ t.pdfPage }}</label><span class="page-label">{{ t.page }}</span><input id="pdf-page" v-model.number="page" type="number" min="1" max="20" step="1"/><a class="document-link" :href="documentUrl()" target="_blank" rel="noopener noreferrer">{{ t.openPdf }}<Icon name="arrow" /></a></div>
      </section>
        <form v-if="editingTitle" class="chat-edit-bar" @submit.prevent="saveTitle"><label class="sr-only" for="chat-title">{{ t.rename }}</label><input id="chat-title" v-model="titleInput" maxlength="80" :placeholder="t.chatTitle" :disabled="loadingHistory" /><button type="submit" :disabled="loadingHistory || !titleInput.trim()">{{ t.save }}</button><button type="button" :disabled="loadingHistory" @click="editingTitle = false">{{ t.cancel }}</button></form>
        <div v-if="deletingChat" class="chat-edit-bar delete-confirm" role="alert"><span>{{ t.deleteConfirm }}</span><button :disabled="loadingHistory" @click="removeChat">{{ t.deleteChat }}</button><button :disabled="loadingHistory" @click="deletingChat = false">{{ t.cancel }}</button></div>
        <div class="message-window">
        <div ref="messageArea" class="messages" role="log" aria-live="polite" :aria-busy="busy" @scroll="onMessageScroll" @wheel="event => { if (event.deltaY < 0) followLatest = false }" @touchmove="followLatest = false" @pointerdown="onScrollPointer" @focusin="followLatest = false" @keydown="event => { if (['ArrowUp', 'PageUp', 'Home'].includes(event.key)) followLatest = false }">
          <div v-if="!messages.length" class="empty-state">
            <div class="hero-symbol"><Icon name="book" /><span><Icon name="shield" /></span></div>
            <span class="hero-kicker">{{ t.heroKicker }}</span>
            <h3>{{ loadingHistory ? t.loadingHistory : t.heroTitle }}</h3><p class="hero-description">{{ t.heroDescription }}</p>
            <div class="prompt-grid"><button v-for="prompt in prompts" :key="prompt.icon" class="prompt-card" :disabled="loadingHistory || !conversationToken" @click="choosePrompt(prompt.question)"><span class="prompt-icon"><Icon :name="prompt.icon" /></span><strong>{{ prompt.title }}</strong><span class="prompt-text">{{ prompt.text }}</span><Icon class="prompt-arrow" name="arrow" /></button></div>
          </div>
          <div v-for="(message, index) in displayMessages" :key="index" class="message" :class="message.role">
            <span class="message-label"><span v-if="message.role === 'assistant'" class="assistant-mark"><Icon name="book" /></span>{{ message.role === 'user' ? t.you : 'InsureTutor' }}</span>
            <div v-if="!message.pending" class="answer-bubble" :class="{ revealing: message.visibleChars !== undefined }">
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
                <summary><Icon name="file" /><span>{{ t.sources }}</span><span class="source-count">{{ message.presentation.groups.length }} {{ t.pages }}</span><Icon name="chevron" /></summary>
                <details v-for="group in message.presentation.groups" :id="`source-${index}-${group.number}`" :key="group.number" class="source-group">
                  <summary>[{{ group.number }}] {{ t.page }} {{ group.page }} · {{ group.sources.length }} {{ t.passages }}</summary>
                  <div class="source-heading"><span>{{ group.documentName }}</span><a :href="group.url" target="_blank" rel="noopener noreferrer">{{ t.openPage }}</a></div>
                  <p class="source-note">{{ t.originalNote }}</p>
                  <blockquote v-for="source in group.sources" :key="source.evidence_id">{{ source.text }}</blockquote>
                </details>
              </details>
              <details class="metrics">
                <summary><Icon name="clock" /><span>{{ t.elapsed }} <strong>{{ (message.reply.metrics.total_ms / 1000).toFixed(1) }} {{ t.seconds }}</strong></span><span class="runtime-label">{{ t.runtime }}</span><Icon name="chevron" /></summary>
                <dl class="request-timings"><div><dt>{{ t.retrieval }}</dt><dd>{{ message.reply.metrics.retrieval_ms }} <small>ms</small></dd></div><div><dt>{{ t.llm }}</dt><dd>{{ (message.reply.metrics.llm_ms / 1000).toFixed(2) }} <small>s</small></dd></div><div><dt>{{ t.total }}</dt><dd>{{ (message.reply.metrics.total_ms / 1000).toFixed(2) }} <small>s</small></dd></div></dl>
                <dl class="request-timings stage-timings"><div v-for="stage in (['ttft_ms', 'generation_ms', 'verification_ms', 'question_resolution_ms'] as const)" :key="stage"><dt>{{ stage === 'ttft_ms' ? t.ttft : stage === 'generation_ms' ? t.generation : stage === 'verification_ms' ? t.verification : t.resolution }}</dt><dd>{{ (stage === 'ttft_ms' ? message.reply.metrics.client_ttft_ms ?? message.reply.metrics.ttft_ms : message.reply.metrics[stage]) == null ? '—' : ((stage === 'ttft_ms' ? message.reply.metrics.client_ttft_ms ?? message.reply.metrics.ttft_ms : message.reply.metrics[stage])! / 1000).toFixed(2) }} <small>s</small></dd></div></dl>
                <p class="usage-line">{{ t.chunks }}: {{ message.reply.metrics.retrieved_chunks }} · {{ t.inputTokens }}: {{ message.reply.metrics.llm_input_tokens }} / {{ t.outputTokens }}: {{ message.reply.metrics.llm_output_tokens }} · {{ t.embedding }}: {{ message.reply.metrics.embedding_input_tokens }}<span v-if="message.reply.metrics.query_cached"> · {{ t.vectorCached }}</span></p>
              </details>
            </template>
          </div>
          <div v-if="busy && awaitingReply" class="waiting-status" role="status"><span class="waiting-dots" aria-hidden="true"><i></i><i></i><i></i></span>{{ streamLabel }}</div>
        </div>
        <button v-if="!followLatest && messages.length" class="jump-latest" type="button" @click="scrollToLatest(true)">↓ {{ t.latest }}</button>
        </div>
        <form class="composer" @submit.prevent="send">
          <p v-if="error" class="error" role="alert">{{ error }}</p>
          <label class="sr-only" for="message">{{ t.question }}</label>
          <div class="input-row"><textarea id="message" ref="composerInput" v-model="input" rows="1" maxlength="2000" :placeholder="t.placeholder" :aria-describedby="'composer-hint'" :disabled="busy || loadingHistory || !conversationToken" @keydown="onComposerKey" /><button type="submit" :aria-label="busy ? t.answering : t.send" :title="busy ? t.answering : t.send" :disabled="busy || loadingHistory || !conversationToken || !input.trim()"><span v-if="busy" class="send-spinner" aria-hidden="true"></span><Icon v-else name="send" /></button></div>
          <div id="composer-hint" class="composer-caption"><span>{{ t.historical }}</span><span class="composer-hint">{{ t.composerHint }}</span></div>
        </form>
      </section>
      </div>
    </div>
    <EvaluationPanel id="performance-view" v-show="activeView === 'performance'" role="tabpanel" aria-labelledby="performance-tab" :language="language" :runs="runs" />
  </main>
</template>
