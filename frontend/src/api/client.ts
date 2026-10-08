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
  request_id?: string
  verification?: { status: string; reason: string | null; detail?: string | null }
  action: string
  message: string
  claims: { text: string; citation_numbers: number[] }[]
  citations: { number: number; evidence_id: string; quote: string; text: string; document_name: string; pdf_page: number; url: string }[]
  metrics: { retrieval_ms: number; llm_ms: number; total_ms: number; retrieved_chunks: number; llm_input_tokens: number; llm_output_tokens: number; embedding_input_tokens: number }
}
async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...options, signal: AbortSignal.timeout(180000) })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail?.message ?? `请求失败（HTTP ${response.status}）`)
  }
  return response.json() as Promise<T>
}
export const getStatus = () => request<AppStatus>('/api/status')
export const askQuestion = (message: string, language: Language) => request<ChatReply>(
  '/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message, language }) },
)
