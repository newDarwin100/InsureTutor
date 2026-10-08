<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { getEvaluations, type EvaluationRow, type Evaluations, type Language } from '../api/client'
import { chartCeiling, latencyHistogram, latencySeries, latencyStats, type TimeMetric } from '../api/latency'
import { copies } from '../copy'

const props = defineProps<{ language: Language; runs: EvaluationRow[] }>()
const t = computed(() => copies[props.language])
const data = ref<Evaluations | null>(null)
const failed = ref(false)
const busy = ref(false)
const dataset = ref('full_trilingual')
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
const hasLLM = computed(() => rows.value.some(row => row.llm_ms != null))
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
watch(dataset, () => { hovered.value = null; if (!hasLLM.value && metric.value === 'llm_ms') metric.value = 'total_ms' })
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
      <span class="sample-count">{{ samples.length }} {{ t.requests }}</span>
    </div>
    <div class="dashboard-toolbar">
      <label>{{ t.dataset }}<select v-model="dataset">
        <option value="live">{{ t.liveRuns }} · {{ runs.length }}</option>
        <optgroup :label="t.historyRuns"><option value="full_trilingual">{{ t.full_trilingual }}</option><option value="full_gold">{{ t.full_gold }}</option><option value="pilot">{{ t.pilot }}</option><option value="answers">{{ t.answers }}</option></optgroup>
      </select></label>
      <div class="stage-switch" :aria-label="t.metric">
        <button v-for="stage in (['total_ms', 'retrieval_ms', 'llm_ms'] as const)" :key="stage" :class="{ active: metric === stage }" :aria-pressed="metric === stage" :disabled="stage === 'llm_ms' && !hasLLM" @click="metric = stage">{{ stage === 'total_ms' ? t.total : stage === 'retrieval_ms' ? t.retrieval : t.llm }}</button>
      </div>
    </div>
    <p class="dashboard-caption">{{ dataset === 'live' ? t.liveNote : t.historyNote }}</p>
    <p v-if="busy && dataset !== 'live'" class="small-note">{{ t.checking }}</p>
    <p v-if="failed && dataset !== 'live'" class="error">{{ t.loadError }} <button class="text-button" @click="load">{{ t.refreshReports }}</button></p>

    <div class="stat-grid">
      <article v-for="(value, key) in { average: stats.average, median: stats.median, minimum: stats.min, maximum: stats.max }" :key="key" class="stat-card">
        <span>{{ label(key) }}</span><strong>{{ seconds(value) }}<small v-if="value != null"> s</small></strong>
      </article>
    </div>

    <div v-if="samples.length" class="chart-grid">
      <article class="chart-card trend-card">
        <div class="chart-heading"><h3>{{ t.trend }}</h3><span>s</span></div>
        <div class="chart-legend"><span><i class="legend-dot request-dot"></i>{{ t.singleTime }}</span><span><i class="legend-line"></i>{{ t.runningAverage }}</span></div>
        <div class="point-readout"><template v-if="selected"><span>#{{ selected.order }}</span><strong>{{ seconds(selected.value) }} s</strong><span>{{ t.runningAverage }} {{ seconds(selected.average) }} s</span></template></div>
        <svg class="latency-chart" viewBox="0 0 710 240" role="img" :aria-label="t.trend" @mouseleave="hovered = null">
          <defs><linearGradient id="latency-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#398771" stop-opacity=".18"/><stop offset="100%" stop-color="#398771" stop-opacity=".01"/></linearGradient></defs>
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
    </div>
    <div v-else class="chart-empty"><span>↗</span><h3>{{ t.chartEmpty }}</h3><p>{{ dataset === 'live' ? t.liveEmpty : t.stageEmpty }}</p></div>

    <div v-if="summary" class="recall-strip"><span>{{ t.recallShort }} <strong>{{ percent(summary.direct_recall) }}</strong></span><span>{{ t.coverageShort }} <strong>{{ percent(summary.expanded_coverage) }}</strong></span></div>
    <details class="run-details">
      <summary>{{ t.runDetails }} <span>{{ rows.length }}</span></summary>
      <div class="evaluation-table" tabindex="0"><table>
        <thead><tr><th>#</th><th>{{ t.question }}</th><th>{{ t.result }}</th><th>{{ t.retrieval }} s</th><th>{{ t.llm }} s</th><th>{{ t.total }} s</th><th>{{ t.inputTokens }}</th><th>{{ t.outputTokens }}</th><th>{{ t.embedding }}</th></tr></thead>
        <tbody><tr v-for="(row, index) in rows" :key="row.id"><td>{{ index + 1 }}</td><td><p>{{ row.question }}</p><small>{{ row.language ?? '—' }} · {{ row.source === 'live' ? t.liveRuns : row.query_cached ? t.cached : row.source }}</small></td><td>{{ label(row.status) }}</td><td>{{ seconds(row.retrieval_ms) }}</td><td>{{ seconds(row.llm_ms) }}</td><td>{{ seconds(row.total_ms) }}</td><td>{{ row.llm_input_tokens ?? '—' }}</td><td>{{ row.llm_output_tokens ?? '—' }}</td><td>{{ row.embedding_input_tokens ?? '—' }}</td></tr></tbody>
      </table></div>
    </details>
    <details class="dashboard-method"><summary>{{ t.method }}</summary><p>{{ t.dashboardMethod }} {{ t.modelTimeNote }}</p><p v-if="data?.missing_reports.length">{{ t.missing }}: {{ data.missing_reports.join(', ') }}</p></details>
  </section>
</template>
