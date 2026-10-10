<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { getEvaluations, type EvaluationRow, type Evaluations, type Language } from '../api/client'
import { averageBreakdown, breakdownStages, chartCeiling, latencyBreakdown, latencyHistogram, latencySeries, latencyStats, type BreakdownStage, type TimeMetric } from '../api/latency'
import { copies } from '../copy'

const props = defineProps<{ language: Language; runs: EvaluationRow[] }>()
const t = computed(() => copies[props.language])
const data = ref<Evaluations | null>(null)
const failed = ref(false)
const busy = ref(false)
const dataset = ref(props.runs.length ? 'live' : 'full_trilingual')
const metric = ref<TimeMetric>('total_ms')
const hovered = ref<number | null>(null)
const rows = computed(() => dataset.value === 'live' ? props.runs : (data.value?.cases ?? []).filter(row => row.group === dataset.value))
const samples = computed(() => latencySeries(rows.value, metric.value))
const values = computed(() => samples.value.map(sample => sample.value))
const stats = computed(() => latencyStats(values.value))
const bins = computed(() => latencyHistogram(values.value))
const ceiling = computed(() => chartCeiling(stats.value.max ?? 0))
const maxBin = computed(() => Math.max(1, ...bins.value.map(bin => bin.count)))
const selected = computed(() => samples.value[hovered.value ?? samples.value.length - 1])
const summary = computed(() => data.value?.summaries.find(item => item.group === dataset.value))
const stages = ['total_ms', 'ttft_ms', 'retrieval_ms', 'llm_ms', 'generation_ms', 'verification_ms', 'question_resolution_ms'] as const
const stageLabels = computed(() => ({ total_ms: t.value.total, ttft_ms: t.value.ttft, retrieval_ms: t.value.retrieval,
  generation_ms: t.value.generation, verification_ms: t.value.verification, question_resolution_ms: t.value.resolution, llm_ms: t.value.llm }))
const label = (value: string) => t.value[value as keyof typeof t.value] ?? value
const seconds = (value: number | null | undefined) => value == null ? '—' : (value / 1000).toFixed(2)
const percent = (value: number | null | undefined) => value == null ? '—' : `${(value * 100).toFixed(1)}%`
const x = (index: number) => samples.value.length === 1 ? 365 : 52 + index / (samples.value.length - 1) * 626
const y = (value: number) => 196 - value / ceiling.value * 162
const line = (field: 'value' | 'average') => samples.value.map((sample, index) => `${x(index)},${y(sample[field])}`).join(' ')
const area = computed(() => samples.value.length ? `${x(0)},196 ${line('value')} ${x(samples.value.length - 1)},196` : '')
const ticks = computed(() => [0, ceiling.value / 2, ceiling.value])
const countTicks = computed(() => [...new Set([0, Math.ceil(maxBin.value / 2), maxBin.value])])
const requestTicks = computed(() => [...new Set([0, Math.floor((samples.value.length - 1) / 2), samples.value.length - 1])])
const barWidth = computed(() => 626 / Math.max(1, bins.value.length))
const breakdown = computed(() => latencyBreakdown(rows.value).sort((a, b) => b.total - a.total))
const breakdownMax = computed(() => chartCeiling(Math.max(0, ...breakdown.value.map(item => item.span))))
const averageParts = computed(() => averageBreakdown(breakdown.value))
const averageTotal = computed(() => latencyStats(breakdown.value.map(item => item.total)).average)
const overviewStats = computed(() => breakdown.value.length ? latencyStats(breakdown.value.map(item => item.total)) : stats.value)
const partLabels = computed(() => ({ retrieval: t.value.retrieval, generation: t.value.generation,
  verification: t.value.verification, resolution: t.value.resolution, model_other: t.value.otherModel, other: t.value.otherTime }))
const partColors: Record<BreakdownStage, string> = { retrieval: '#7796e7', generation: '#4fbaad',
  verification: '#b090d2', resolution: '#edba67', model_other: '#91a5b1', other: '#cdd5df' }
watch(dataset, () => { hovered.value = null; if (!rows.value.some(row => row[metric.value] != null)) metric.value = 'total_ms' })
watch(metric, () => { hovered.value = null })
watch(() => props.runs.length, (count, previous) => { if (count && !previous) dataset.value = 'live' })
async function load() {
  if (busy.value) return
  busy.value = true
  failed.value = false
  try { data.value = await getEvaluations() } catch { failed.value = true } finally { busy.value = false }
}
onMounted(load)
</script>

<template>
  <section class="performance-panel">
    <div class="dashboard-heading">
      <div><span class="eyebrow">INSURETUTOR / PERFORMANCE</span><h2>{{ t.performance }}</h2></div>
      <span class="sample-count">{{ breakdown.length || samples.length }} {{ t.requests }}</span>
    </div>
    <div class="dashboard-toolbar">
      <label>{{ t.dataset }}<select v-model="dataset">
        <option value="live">{{ t.liveRuns }} · {{ runs.length }}</option>
        <optgroup :label="t.historyRuns"><option value="full_trilingual">{{ t.full_trilingual }}</option><option value="full_gold">{{ t.full_gold }}</option><option value="pilot">{{ t.pilot }}</option><option value="answers">{{ t.answers }}</option></optgroup>
      </select></label>
    </div>
    <p class="dashboard-caption">{{ dataset === 'live' ? t.liveNote : t.historyNote }}</p>
    <p v-if="busy && dataset !== 'live'" class="small-note">{{ t.checking }}</p>
    <p v-if="failed && dataset !== 'live'" class="error">{{ t.loadError }} <button class="text-button" @click="load">{{ t.refreshReports }}</button></p>

    <div class="stat-grid">
      <article v-for="(value, key) in { average: overviewStats.average, median: overviewStats.median, minimum: overviewStats.min, maximum: overviewStats.max }" :key="key" class="stat-card">
        <span>{{ label(key) }}</span><strong>{{ seconds(value) }}<small v-if="value != null"> s</small></strong>
      </article>
    </div>

    <div v-if="breakdown.length" class="chart-grid breakdown-grid">
      <article class="chart-card">
        <div class="chart-heading"><h3>{{ t.breakdown }}</h3><span>{{ t.total }} · s · {{ t.slowestFirst }}</span></div>
        <div class="chart-legend phase-legend"><span v-for="part in averageParts" :key="part.stage"><i class="legend-dot" :style="{ background: partColors[part.stage] }"></i>{{ partLabels[part.stage] }}</span></div>
        <div class="breakdown-axis"><span>0</span><span>{{ seconds(breakdownMax / 2) }}</span><span>{{ seconds(breakdownMax) }} s</span></div>
        <div class="request-bars">
          <div v-for="item in breakdown" :key="item.row.id" class="request-bar-row">
            <div class="request-bar-heading"><span class="request-number">#{{ item.order }}</span><span class="request-bar-question" :title="item.row.question">{{ item.row.question }}</span><strong>{{ seconds(item.total) }} s</strong></div>
            <div class="request-bar-track" role="img" :aria-label="`#${item.order}: ${item.row.question}, ${t.total} ${seconds(item.total)} s`">
              <span v-for="stage in breakdownStages" :key="stage" :style="{ width: `${item.parts[stage] / breakdownMax * 100}%`, background: partColors[stage] }" :title="`${partLabels[stage]}: ${seconds(item.parts[stage])} s`"></span>
            </div>
            <div class="request-bar-values"><span v-for="part in averageParts.filter(part => item.parts[part.stage] > 0)" :key="part.stage"><i :style="{ background: partColors[part.stage] }"></i>{{ partLabels[part.stage] }} {{ seconds(item.parts[part.stage]) }}s</span><span v-if="item.total === 0">0 s</span></div>
          </div>
        </div>
      </article>
      <article class="chart-card">
        <div class="chart-heading"><h3>{{ t.timeShare }}</h3><span>{{ breakdown.length }} {{ t.requests }}</span></div>
        <div class="donut-layout">
          <svg class="time-donut" viewBox="0 0 144 144" role="img" :aria-label="t.timeShare">
            <circle cx="72" cy="72" r="54" fill="none" stroke="#eef1f6" stroke-width="16"/>
            <circle v-for="part in averageParts" :key="part.stage" cx="72" cy="72" r="54" pathLength="100" fill="none" :stroke="partColors[part.stage]" stroke-width="16" :stroke-dasharray="`${part.share * 100} ${100 - part.share * 100}`" :stroke-dashoffset="-part.offset * 100" transform="rotate(-90 72 72)"><title>{{ partLabels[part.stage] }}: {{ seconds(part.mean) }} s · {{ (part.share * 100).toFixed(1) }}%</title></circle>
            <text x="72" y="70" text-anchor="middle" class="donut-total">{{ seconds(averageTotal) }}s</text><text x="72" y="88" text-anchor="middle" class="donut-caption">{{ t.average }}</text>
          </svg>
          <div class="donut-legend"><div v-for="part in averageParts" :key="part.stage"><span><i :style="{ background: partColors[part.stage] }"></i>{{ partLabels[part.stage] }}</span><strong>{{ (part.share * 100).toFixed(1) }}%</strong><small>{{ seconds(part.mean) }} s</small></div></div>
        </div>
        <p class="breakdown-note">{{ t.breakdownNote }}</p>
      </article>
    </div>
    <details v-if="samples.length" class="chart-extras"><summary>{{ t.trendAndDistribution }}</summary>
      <div class="stage-switch" :aria-label="t.metric">
        <button v-for="stage in stages" :key="stage" :class="{ active: metric === stage }" :aria-pressed="metric === stage" :disabled="!rows.some(row => row[stage] != null)" @click="metric = stage">{{ stageLabels[stage] }}</button>
      </div><div class="chart-grid">
      <article class="chart-card trend-card">
        <div class="chart-heading"><h3>{{ t.trend }}</h3><span>s</span></div>
        <div class="chart-legend"><span><i class="legend-dot request-dot"></i>{{ t.singleTime }}</span><span><i class="legend-line"></i>{{ t.runningAverage }}</span></div>
        <div class="point-readout"><template v-if="selected"><span>#{{ selected.order }}</span><strong>{{ seconds(selected.value) }} s</strong><span>{{ t.runningAverage }} {{ seconds(selected.average) }} s</span></template></div>
        <svg class="latency-chart" viewBox="0 0 710 240" role="img" :aria-label="t.trend" @mouseleave="hovered = null">
          <defs><linearGradient id="latency-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#7492e5" stop-opacity=".16"/><stop offset="100%" stop-color="#7492e5" stop-opacity=".01"/></linearGradient></defs>
          <g v-for="tick in ticks" :key="tick"><line x1="52" x2="678" :y1="y(tick)" :y2="y(tick)" class="chart-gridline"/><text x="42" :y="y(tick) + 4" text-anchor="end">{{ (tick / 1000).toFixed(1) }}</text></g>
          <polygon :points="area" fill="url(#latency-fill)"/>
          <polyline :points="line('value')" class="request-line"/>
          <polyline :points="line('average')" class="average-line"/>
          <line v-if="selected" :x1="x(selected.order - 1)" :x2="x(selected.order - 1)" y1="28" y2="196" class="hover-guide"/>
          <circle v-for="(sample, index) in samples" :key="sample.row.id" :cx="x(index)" :cy="y(sample.value)" :r="hovered === index ? 6 : 4" class="request-point" tabindex="0" :aria-label="`#${sample.order}: ${seconds(sample.value)} s, ${t.runningAverage} ${seconds(sample.average)} s`" @mouseenter="hovered = index" @focus="hovered = index" @blur="hovered = null">
            <title>#{{ sample.order }} · {{ seconds(sample.value) }} s</title>
          </circle>
          <g v-for="index in requestTicks" :key="index"><text :x="x(index)" y="219" text-anchor="middle">{{ index + 1 }}</text></g>
        </svg>
        <div class="chart-footer"><span>{{ dataset === 'live' ? t.requestOrder : t.caseOrder }}</span><span>{{ t.viewHint }}</span></div>
      </article>
      <article class="chart-card distribution-card">
        <div class="chart-heading"><h3>{{ t.distribution }}</h3><span>{{ t.requestCount }}</span></div>
        <p class="distribution-subtitle">{{ t.timeRange }} · s</p>
        <svg class="latency-chart histogram-chart" viewBox="0 0 710 240" role="img" :aria-label="t.distribution">
          <g v-for="tick in countTicks" :key="tick"><line x1="52" x2="678" :y1="196 - tick / maxBin * 150" :y2="196 - tick / maxBin * 150" class="chart-gridline"/><text x="42" :y="200 - tick / maxBin * 150" text-anchor="end">{{ tick }}</text></g>
          <g v-for="(bin, index) in bins" :key="index">
            <rect :x="52 + index * barWidth + 7" :y="196 - bin.count / maxBin * 150" :width="barWidth - 14" :height="bin.count / maxBin * 150" rx="5" class="histogram-bar">
              <title>{{ seconds(bin.low) }}–{{ seconds(bin.high) }} s: {{ bin.count }} {{ t.countUnit }}</title>
            </rect>
            <text :x="52 + (index + .5) * barWidth" :y="187 - bin.count / maxBin * 150" text-anchor="middle" class="bar-count">{{ bin.count || '' }}</text>
            <text :x="52 + index * barWidth" y="219" text-anchor="middle">{{ (bin.low / 1000).toFixed(1) }}</text>
          </g>
          <text x="678" y="219" text-anchor="middle">{{ ((bins.at(-1)?.high ?? 0) / 1000).toFixed(1) }}</text>
        </svg>
        <div class="chart-footer"><span>{{ t.minimum }} {{ seconds(stats.min) }} s</span><span>{{ t.maximum }} {{ seconds(stats.max) }} s</span></div>
      </article>
    </div></details>
    <div v-else class="chart-empty"><span>↗</span><h3>{{ t.chartEmpty }}</h3><p>{{ dataset === 'live' ? t.liveEmpty : t.stageEmpty }}</p></div>

    <div v-if="summary" class="recall-strip"><span>{{ t.recallShort }} <strong>{{ percent(summary.direct_recall) }}</strong></span><span>{{ t.coverageShort }} <strong>{{ percent(summary.expanded_coverage) }}</strong></span></div>
    <details class="run-details">
      <summary>{{ t.runDetails }} <span>{{ rows.length }}</span></summary>
      <div class="evaluation-table" tabindex="0"><table>
        <thead><tr><th>#</th><th>{{ t.question }}</th><th>{{ t.result }}</th><th>{{ t.ttft }} s</th><th>{{ t.retrieval }} s</th><th>{{ t.generation }} s</th><th>{{ t.verification }} s</th><th>{{ t.resolution }} s</th><th>{{ t.llm }} s</th><th>{{ t.total }} s</th><th>{{ t.inputTokens }}</th><th>{{ t.outputTokens }}</th><th>{{ t.embedding }}</th></tr></thead>
        <tbody><tr v-for="(row, index) in rows" :key="row.id"><td>{{ index + 1 }}</td><td><p>{{ row.question }}</p><small>{{ row.language ?? '—' }} · {{ row.source === 'live' ? t.liveRuns : row.source === 'saved_chat' ? t.savedChatRuns : row.query_cached ? t.cached : row.source }}</small></td><td>{{ label(row.status) }}</td><td>{{ seconds(row.ttft_ms) }}</td><td>{{ seconds(row.retrieval_ms) }}</td><td>{{ seconds(row.generation_ms) }}</td><td>{{ seconds(row.verification_ms) }}</td><td>{{ seconds(row.question_resolution_ms) }}</td><td>{{ seconds(row.llm_ms) }}</td><td>{{ seconds(row.total_ms) }}</td><td>{{ row.llm_input_tokens ?? '—' }}</td><td>{{ row.llm_output_tokens ?? '—' }}</td><td>{{ row.embedding_input_tokens ?? '—' }}</td></tr></tbody>
      </table></div>
    </details>
    <details class="dashboard-method"><summary>{{ t.method }}</summary><p>{{ t.dashboardMethod }} {{ t.modelTimeNote }} {{ t.ttftNote }}</p><p v-if="data?.missing_reports.length">{{ t.missing }}: {{ data.missing_reports.join(', ') }}</p></details>
  </section>
</template>
