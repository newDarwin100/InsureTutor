<script setup lang="ts">
import { computed, ref } from 'vue'
import { getEvaluations, type Evaluations, type Language } from '../api/client'
import { copies } from '../copy'
const props = defineProps<{ language: Language }>()
const t = computed(() => copies[props.language])
const data = ref<Evaluations | null>(null)
const failed = ref(false)
const busy = ref(false)
const filter = ref('all')
const rows = computed(() => (data.value?.cases ?? []).filter(row => filter.value === 'all' || row.kind === filter.value))
const label = (value: string) => t.value[value as keyof typeof t.value] ?? value
const number = (value: number | null | undefined, unit = '') => value == null ? '—' : `${value.toLocaleString()}${unit}`
const percent = (value: number | null | undefined) => value == null ? '—' : `${(value * 100).toFixed(2)}%`
async function load(event: Event) {
  if (!(event.target as HTMLDetailsElement).open || data.value || busy.value) return
  busy.value = true
  failed.value = false
  try { data.value = await getEvaluations() } catch { failed.value = true } finally { busy.value = false }
}
</script>
<template>
  <details class="evaluation panel" @toggle="load">
    <summary>{{ t.dashboard }}</summary>
    <p class="small-note">{{ t.reportNote }}</p>
    <p class="small-note">{{ t.limitations }}</p>
    <p v-if="busy" class="small-note">{{ t.checking }}</p>
    <p v-if="failed" class="error">{{ t.loadError }}</p>
    <template v-if="data">
      <div class="evaluation-summaries">
        <article v-for="summary in data.summaries" :key="summary.group">
          <h3>{{ label(summary.group) }}</h3>
          <p>{{ t.direct }}: <strong>{{ percent(summary.direct_recall) }}</strong></p>
          <p>{{ t.expanded }}: {{ percent(summary.expanded_coverage) }}</p>
          <small>{{ summary.model }} · {{ summary.measured_at?.slice(0, 10) }} · {{ summary.source }}</small>
        </article>
      </div>
      <label class="language-label">{{ t.result }}
        <select v-model="filter"><option value="all">{{ t.all }}</option><option value="retrieval">{{ t.retrievalOnly }}</option><option value="answer">{{ t.answerRuns }}</option></select>
      </label>
      <div class="evaluation-table" tabindex="0">
        <table>
          <thead><tr><th>{{ t.question }}</th><th>{{ t.result }}</th><th>{{ t.retrieval }} ms</th><th>{{ t.llm }} ms</th><th>{{ t.total }} ms</th><th>{{ t.chunks }}</th><th>{{ t.embedding }}</th><th>{{ t.inputTokens }}</th><th>{{ t.outputTokens }}</th></tr></thead>
          <tbody><tr v-for="row in rows" :key="row.id">
            <td><strong>{{ row.id }}</strong><p>{{ row.question }}</p><small>{{ row.language ?? '—' }} · {{ row.source }}<br />{{ row.measured_at ?? '—' }}<br />{{ row.model ?? '—' }}<br />{{ row.query_cached ? t.cached : '' }}</small></td>
            <td>{{ label(row.provenance) }}<br />{{ label(row.status) }}<small v-if="row.direct_recall != null"><br />{{ t.direct }}: {{ percent(row.direct_recall) }}<br />{{ t.expanded }}: {{ percent(row.expanded_coverage) }}</small></td>
            <td>{{ number(row.retrieval_ms) }}</td><td>{{ number(row.llm_ms) }}</td><td>{{ number(row.total_ms) }}</td><td>{{ number(row.chunks) }}</td><td>{{ number(row.embedding_input_tokens) }}</td><td>{{ number(row.llm_input_tokens) }}</td><td>{{ number(row.llm_output_tokens) }}</td>
          </tr></tbody>
        </table>
      </div>
      <p v-if="!rows.length" class="small-note">{{ t.empty }}</p>
      <p v-if="data.missing_reports.length" class="small-note">{{ t.missing }}: {{ data.missing_reports.join(', ') }}</p>
    </template>
  </details>
</template>
