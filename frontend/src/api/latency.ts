import type { EvaluationRow } from './client'

export type TimeMetric = 'total_ms' | 'retrieval_ms' | 'llm_ms' | 'ttft_ms' | 'generation_ms' | 'verification_ms' | 'question_resolution_ms'

export const breakdownStages = ['retrieval', 'generation', 'verification', 'resolution', 'model_other', 'other'] as const
export type BreakdownStage = typeof breakdownStages[number]
const measured = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value) && value >= 0

// LLM and first-text times overlap the stages: never add them as extra slices.
// Older reports may omit generation/check details; retain that model time explicitly.
export function latencyBreakdown(rows: EvaluationRow[]) {
  return rows.flatMap((row, index) => {
    if (row.provenance === 'not_run' || !measured(row.total_ms)) return []
    const value = (field: keyof EvaluationRow) => measured(row[field]) ? row[field] as number : 0
    const parts: Record<BreakdownStage, number> = {
      retrieval: value('retrieval_ms'), generation: value('generation_ms'),
      verification: value('verification_ms'), resolution: value('question_resolution_ms'),
      model_other: 0, other: 0,
    }
    const modelParts = parts.generation + parts.verification + parts.resolution
    parts.model_other = Math.max(0, value('llm_ms') - modelParts)
    const known = Object.values(parts).reduce((sum, duration) => sum + duration, 0)
    parts.other = Math.max(0, row.total_ms - known)
    return [{ row, order: index + 1, total: row.total_ms, span: Math.max(row.total_ms, known), parts }]
  })
}

export function averageBreakdown(samples: ReturnType<typeof latencyBreakdown>) {
  const sums = Object.fromEntries(breakdownStages.map(stage => [stage, 0])) as Record<BreakdownStage, number>
  for (const sample of samples) for (const stage of breakdownStages) sums[stage] += sample.parts[stage]
  const sum = Object.values(sums).reduce((total, value) => total + value, 0)
  let offset = 0
  return breakdownStages.map(stage => {
    const share = sum ? sums[stage] / sum : 0
    const slice = { stage, mean: samples.length ? sums[stage] / samples.length : 0, share, offset }
    offset += share
    return slice
  }).filter(slice => slice.mean > 0)
}

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
