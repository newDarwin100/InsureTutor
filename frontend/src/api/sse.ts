/** Decode arbitrary UTF-8/network boundaries. Status/heartbeats are not answer tokens. */
export async function consumeSSE(body: ReadableStream<Uint8Array>, onEvent: (event: string, data: any) => void) {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true })
      if (buffer.length > 2_000_000) throw new Error('Stream frame too large')
      let boundary: RegExpMatchArray | null
      while ((boundary = buffer.match(/\r?\n\r?\n/))) {
        const frame = buffer.slice(0, boundary.index)
        buffer = buffer.slice(boundary.index! + boundary[0].length)
        let event = 'message'
        const data: string[] = []
        for (const line of frame.split(/\r?\n/)) {
          if (line.startsWith('event:')) event = line.slice(6).trim()
          if (line.startsWith('data:')) data.push(line.slice(5).replace(/^ /, ''))
        }
        if (data.length) {
          onEvent(event, JSON.parse(data.join('\n')))
          if (event === 'done') { await reader.cancel(); return }
        }
      }
      if (done) throw new Error('Stream ended without a final response')
    }
  } catch (error) {
    await reader.cancel().catch(() => {})
    throw error
  } finally { reader.releaseLock() }
}
