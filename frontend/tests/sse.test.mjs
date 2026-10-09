import { readFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import test from 'node:test'
import ts from 'typescript'
const source = readFileSync(new URL('../src/api/sse.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } }).outputText
const { consumeSSE } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)
const stream = text => new ReadableStream({ start(controller) {
  for (const byte of new TextEncoder().encode(text)) controller.enqueue(Uint8Array.of(byte))
  controller.close()
} })

test('UTF-8 split on every byte and SSE frames preserve paragraphs; status is not answer text', async () => {
  const events = []
  await consumeSSE(stream(': heartbeat\r\n\r\nevent: status\r\ndata: {"stage":"retrieval"}\r\n\r\nevent: delta\ndata: {"index":0,"text":"不是🙂"}\n\nevent: done\ndata: {"claims":[]}\n\n'), (e, d) => events.push([e, d]))
  assert.deepEqual(events, [['status', { stage: 'retrieval' }], ['delta', { index: 0, text: '不是🙂' }], ['done', { claims: [] }]])
})
test('partial reply followed by EOF cannot become a completed answer', async () => {
  await assert.rejects(consumeSSE(stream('event: delta\ndata: {"text":"draft"}\n\n'), () => {}), /without a final/)
})
test('server error stops reading and malformed events fail', async () => {
  await assert.rejects(consumeSSE(stream('event: error\ndata: {"code":"MODEL_UNAVAILABLE"}\n\n'), (e, d) => { if (e === 'error') throw new Error(d.code) }), /MODEL_UNAVAILABLE/)
  await assert.rejects(consumeSSE(stream('event: delta\ndata: broken\n\n'), () => {}), SyntaxError)
})
