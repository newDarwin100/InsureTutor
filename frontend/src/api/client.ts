export interface AppStatus {
  stage: string
  backend_ready: boolean
  rag_ready: boolean
  document_available: boolean
  api_key_configured: boolean
  knowledge_counts: Record<string, number>
}
export type Language = 'en' | 'zh-Hans' | 'zh-Hant'
export interface ChatReply {
  language?: Language
  request_id?: string
  verification?: { status: string; reason: string | null; detail?: string | null }
  action: string
  message: string
  claims: { text: string; citation_numbers: number[] }[]
  citations: { number: number; evidence_id: string; quote: string; text: string; document_name: string; pdf_page: number; url: string }[]
  metrics: { retrieval_ms: number; llm_ms: number; total_ms: number; retrieved_chunks: number; llm_input_tokens: number; llm_output_tokens: number; embedding_input_tokens: number }
}
export class ApiError extends Error {
  constructor(public code: string, public status: number) { super(code) }
}
async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...options, signal: AbortSignal.timeout(180000) })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(body?.detail?.code ?? 'REQUEST_FAILED', response.status)
  }
  return response.json() as Promise<T>
}
export const getStatus = () => request<AppStatus>('/api/status')
export interface ConversationSummary { token: string; title: string; created: number; updated: number; language: Language }
export interface SavedMessage { role: 'user' | 'assistant'; text: string; reply: ChatReply | null; language: Language; status: string; error_code: string | null }
export interface SavedConversation extends ConversationSummary { messages: SavedMessage[] }
export const createWorkspace = () => request<{ token: string }>('/api/workspaces', { method: 'POST' })
export const listConversations = (token: string) => request<{ conversations: ConversationSummary[] }>('/api/conversations', { headers: { 'X-Workspace-Token': token } })
export const createConversation = (workspace?: string) => request<{ token: string }>('/api/conversations', { method: 'POST', headers: workspace ? { 'X-Workspace-Token': workspace } : undefined })
export const getConversation = (token: string) => request<SavedConversation>('/api/conversations/current', { headers: { 'X-Conversation-Token': token } })
export const renameConversation = (token: string, title: string) => request('/api/conversations/current', { method: 'PATCH', headers: { 'Content-Type': 'application/json', 'X-Conversation-Token': token }, body: JSON.stringify({ title }) })
export const deleteConversation = (token: string) => request('/api/conversations/current', { method: 'DELETE', headers: { 'X-Conversation-Token': token } })
export const askQuestion = (message: string, language: Language | 'auto', token: string) => request<ChatReply>(
  '/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Conversation-Token': token }, body: JSON.stringify({ message, language }) },
)

export interface EvaluationRow {
  id: string; group: string; source: string; kind: 'retrieval' | 'answer'; provenance: 'real' | 'not_run'
  question: string; language: string | null; status: string; measured_at: string | null; model: string | null
  retrieval_ms: number | null; llm_ms: number | null; total_ms: number | null; chunks: number | null
  embedding_input_tokens: number | null; llm_input_tokens: number | null; llm_output_tokens: number | null
  direct_recall: number | null; expanded_coverage: number | null; query_cached: boolean
}
export interface Evaluations {
  summaries: { group: string; source: string; direct_recall: number | null; expanded_coverage: number | null; model: string | null; measured_at: string | null }[]
  cases: EvaluationRow[]; missing_reports: string[]; live_model_called: false; quality_benchmark_complete: false
}
export const getEvaluations = () => request<Evaluations>('/api/evaluations')
