import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('../src/api/reveal.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText
const { characterCount, revealParagraphs, revealBudget } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)

test('progressive text keeps paragraph order and delays references until their text is complete', () => {
  const paragraphs = [{ text: '非保证🙂', references: [1] }, { text: '提款条件', references: [2, 3] }]
  assert.equal(characterCount(paragraphs[0].text), 4)
  assert.deepEqual(revealParagraphs(paragraphs, 0), [])
  assert.deepEqual(revealParagraphs(paragraphs, 3), [{ text: '非保证', references: [] }])
  assert.deepEqual(revealParagraphs(paragraphs, 5), [paragraphs[0], { text: '提', references: [] }])
  assert.deepEqual(revealParagraphs(paragraphs, Infinity), paragraphs)
  assert.equal(paragraphs[1].text, '提款条件')
})

test('elapsed time reveals monotonically, with long answers completing within five seconds', () => {
  for (const length of [12, 300, 1800]) {
    assert.equal(revealBudget(0, length), 0)
    assert.ok(revealBudget(100, length) < revealBudget(300, length))
    assert.equal(revealBudget(5000, length), length)
    assert.equal(revealBudget(9000, length), length)
  }
})
