export interface AppStatus {
  stage: string
  backend_ready: boolean
  rag_ready: boolean
  document_available: boolean
  api_key_configured: boolean
  knowledge_counts: Record<string, number>
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...options, signal: AbortSignal.timeout(15000) })
  if (!response.ok) throw new Error(`请求失败（HTTP ${response.status}）`)
  return response.json() as Promise<T>
}

export const getStatus = () => request<AppStatus>('/api/status')
export const testConnection = (message: string) => request<{ mode: string; received: string; message: string }>(
  '/api/demo', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message }) },
)
