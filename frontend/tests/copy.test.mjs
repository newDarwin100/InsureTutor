import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import ts from 'typescript'
const source = readFileSync(new URL('../src/copy.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText
const { copies } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)
test('all interface languages include the same labels and errors', () => {
  const keys = Object.keys(copies.en).sort()
  for (const lang of ['zh-Hans', 'zh-Hant', 'en']) {
    assert.deepEqual(Object.keys(copies[lang]).sort(), keys)
    assert.ok(Object.values(copies[lang]).every(value => typeof value === 'string' && value.length))
  }
  assert.equal(copies.en.send, 'Send')
  assert.equal(copies['zh-Hant'].send, '發送')
})
