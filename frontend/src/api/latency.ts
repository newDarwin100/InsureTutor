import type { EvaluationRow } from './client'

export type TimeMetric = 'total_ms' | 'retrieval_ms' | 'llm_ms' | 'ttft_ms' | 'generation_ms' | 'verification_ms' | 'question_resolution_ms'

export function latencySeries(rows: EvaluationRow[], metric: TimeMetric) {
  let sum = 0
  return rows.filter(row => row.provenance !== 'not_run' && typeof row[metric] === 'number'
    && Number.isFinite(row[metric]) && row[metric]! >= 0).map((row, index) => {
    const value = row[metric]!
    sum += value
    return { row, value, order: index + 1, average: sum / (index + 1) }
  })
}

export function latencyStats(values: number[]) {
  if (!values.length) return { average: null, median: null, min: null, max: null }
  const sorted = [...values].sort((a, b) => a - b)
  const middle = Math.floor(sorted.length / 2)
  return { average: values.reduce((sum, value) => sum + value, 0) / values.length,
    median: sorted.length % 2 ? sorted[middle]! : (sorted[middle - 1]! + sorted[middle]!) / 2,
    min: sorted[0]!, max: sorted[sorted.length - 1]! }
}

export function chartCeiling(max: number) {
  const magnitude = 10 ** Math.floor(Math.log10(Math.max(max, 1000)))
  return ([1, 2, 5, 10].find(step => step * magnitude >= max) ?? 10) * magnitude
}

export function latencyHistogram(values: number[]) {
  if (!values.length) return []
  const upper = chartCeiling(Math.max(...values))
  const count = Math.min(8, Math.max(4, Math.ceil(Math.log2(values.length) + 1)))
  const width = upper / count
  const bins = Array.from({ length: count }, (_, index) => ({
    low: index * width, high: (index + 1) * width, count: 0,
  }))
  for (const value of values) bins[Math.min(count - 1, Math.floor(value / width))]!.count++
  return bins
}
