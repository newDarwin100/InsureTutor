import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('../src/api/latency.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText
const { averageBreakdown, latencyBreakdown, latencySeries, latencyStats, latencyHistogram, chartCeiling } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)
const row = (id, value, provenance = 'real') => ({ id, total_ms: value, provenance })

test('cumulative mean excludes unknown and unexecuted timings but includes real zero', () => {
  const series = latencySeries([row('blocked', 0), row('a', 1000), row('missing', null),
    row('unrun', 5000, 'not_run'), row('b', 3000), row('bad', NaN), row('infinite', Infinity)], 'total_ms')
  assert.deepEqual(series.map(s => s.row.id), ['blocked', 'a', 'b'])
  assert.deepEqual(series.map(s => s.average), [0, 500, 4000 / 3])
  assert.deepEqual(latencyStats(series.map(s => s.value)), { average: 4000 / 3, median: 1000, min: 0, max: 3000 })
})

test('histogram counts every sample exactly once, including upper boundary and repeated timings', () => {
  for (const values of [[0, 0, 0], [1000], [500, 1000, 2000, 2000], [2300, 5700, 10000]]) {
    const bins = latencyHistogram(values)
    assert.equal(bins.reduce((sum, bin) => sum + bin.count, 0), values.length)
    assert.ok(bins.at(-1).high >= Math.max(...values))
    const last = values.at(-1)
    assert.ok(bins.some((bin, index) => bin.count && last >= bin.low && (last < bin.high || index === bins.length - 1)))
  }
  assert.deepEqual(latencyStats([]), { average: null, median: null, min: null, max: null })
  assert.deepEqual(latencyHistogram([]), [])
  assert.equal(latencyStats([1000, 3000]).median, 2000)
  assert.ok(chartCeiling(12730) >= 12730)
})

test('time composition does not double-count model totals or first-text time', () => {
  const samples = latencyBreakdown([{ ...row('a', 10000), ttft_ms: 10000,
    retrieval_ms: 1000, generation_ms: 6000, verification_ms: 1500,
    question_resolution_ms: 1000, llm_ms: 8500 }])
  assert.deepEqual(samples[0].parts, { retrieval: 1000, generation: 6000,
    verification: 1500, resolution: 1000, model_other: 0, other: 500 })
  const average = averageBreakdown(samples)
  assert.equal(average.find(part => part.stage === 'generation').share, .6)
  assert.equal(average.reduce((sum, part) => sum + part.share, 0), 1)
})

test('old reports retain unknown model stages and empty or invalid measurements are excluded', () => {
  const samples = latencyBreakdown([{ ...row('old', 5000), retrieval_ms: 1000, llm_ms: 3800 },
    row('blocked', 0), row('missing', null), row('unrun', 9000, 'not_run'), row('invalid', Infinity)])
  assert.equal(samples.length, 2)
  assert.equal(samples[0].parts.model_other, 3800)
  assert.equal(samples[0].parts.other, 200)
  assert.equal(samples[0].parts.generation, 0)
  assert.equal(averageBreakdown(samples).find(part => part.stage === 'model_other').mean, 1900)
  assert.deepEqual(averageBreakdown([]), [])
})
