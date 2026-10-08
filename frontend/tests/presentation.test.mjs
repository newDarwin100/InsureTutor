import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('../src/api/presentation.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText
const { presentReply } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)
const citation = (number, page, evidenceId, documentName = 'Insurance.pdf') => ({
  number, pdf_page: page, evidence_id: evidenceId, document_name: documentName,
  url: `/api/documents/${documentName}#page=${page}`, text: `Original ${evidenceId}`,
})

test('page references collapse duplicate markers without losing evidence', () => {
  const reply = { claims: [{ text: 'A complete answer.', citation_numbers: [1, 2, 3, 1] }],
    citations: [citation(1, 12, 'zh-note'), citation(2, 12, 'en-note'), citation(3, 10, 'conditions')] }
  const view = presentReply(reply)
  assert.equal(view.groups.length, 2)
  assert.deepEqual(view.paragraphs[0].references, [1, 2])
  assert.deepEqual(view.groups[0].sources.map(s => s.evidence_id), ['zh-note', 'en-note'])
  assert.equal(view.groups[0].url, '/api/documents/Insurance.pdf#page=12')
  assert.equal(reply.claims[0].citation_numbers.length, 4) // The underlying citation mapping is unchanged.
})

test('different documents on the same page remain separate', () => {
  const view = presentReply({ claims: [], citations: [citation(1, 12, 'one'), citation(2, 12, 'two', 'Other.pdf')] })
  assert.equal(view.groups.length, 2)
})

test('refusals have no empty source groups', () => {
  assert.deepEqual(presentReply({ claims: [], citations: [] }), { groups: [], paragraphs: [] })
})
