// Reveal checked text only. References appear once their whole paragraph is visible.
export function revealParagraphs<T extends { text: string; references: number[] }>(paragraphs: T[], budget: number) {
  let remaining = Math.max(0, budget)
  return paragraphs.flatMap(paragraph => {
    const characters = Array.from(paragraph.text)
    if (remaining <= 0) return []
    const visible = characters.slice(0, remaining).join('')
    remaining -= characters.length
    return [{ ...paragraph, text: visible, references: visible === paragraph.text ? paragraph.references : [] }]
  })
}

export function characterCount(text: string) { return Array.from(text).length }

export function revealBudget(elapsed: number, total: number) {
  // Keep long answers readable without adding an unbounded wait.
  const duration = Math.min(5000, Math.max(600, total / 100 * 1000))
  return Math.min(total, Math.ceil(Math.max(0, elapsed) / duration * total))
}
