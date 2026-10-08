import type { ChatReply } from './client'

// Group display references by document/page; retain every underlying evidence item.
export function presentReply(reply: ChatReply) {
  const groups: { number: number; documentName: string; page: number; url: string; sources: ChatReply['citations'] }[] = []
  const displayNumber = new Map<number, number>()
  for (const source of reply.citations) {
    let group = groups.find(g => g.documentName === source.document_name && g.page === source.pdf_page && g.url === source.url)
    if (!group) {
      group = { number: groups.length + 1, documentName: source.document_name, page: source.pdf_page, url: source.url, sources: [] }
      groups.push(group)
    }
    if (!group.sources.some(s => s.evidence_id === source.evidence_id)) group.sources.push(source)
    displayNumber.set(source.number, group.number)
  }
  return {
    groups,
    paragraphs: reply.claims.map(claim => ({
      text: claim.text,
      references: [...new Set(claim.citation_numbers.map(n => displayNumber.get(n)).filter((n): n is number => n !== undefined))],
    })),
  }
}
