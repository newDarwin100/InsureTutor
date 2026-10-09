<script setup lang="ts">
defineProps<{ name: string }>()
const paths: Record<string, string> = {
  book: 'M12 6.5C9 4 5.5 4 3 5v14c2.5-1 6-1 9 1.5C15 18 18.5 18 21 19V5c-2.5-1-6-1-9 1.5Zm0 0v14',
  chat: 'M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-1 1v-9.5A8.5 8.5 0 0 1 11.5 3h1a8.5 8.5 0 0 1 8.5 8.5ZM7 9h10M7 13h6',
  chart: 'M4 4v16h16M8 15l4-5 4 3 4-7',
  plus: 'M12 5v14M5 12h14',
  file: 'M14 3H5v18h14V8l-5-5Zm0 0v5h5M8 12h8M8 16h5',
  arrow: 'M7 17 17 7M7 7h10v10',
  send: 'M12 19V5M5 12l7-7 7 7',
  edit: 'm15 4 5 5M4 20l5-1L21 7l-5-5L4 14v6Z',
  trash: 'M3 6h18M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7M14 10v7',
  menu: 'M4 6h16M4 12h16M4 18h16',
  close: 'm6 6 12 12M6 18 18 6',
  shield: 'M12 3 3 7v5c0 5 9 9 9 9s9-4 9-9V7l-9-4Zm-4 9 3 3 5-6',
  wallet: 'M20 8V5H5a2 2 0 0 0 0 4h16v11H5a2 2 0 0 1-2-2V7M21 12h-6v5h6M17 14.5h.01',
  clock: 'M12 8v4l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0Z',
  chevron: 'm9 5 7 7-7 7',
  globe: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM3 12h18M12 3c5 5 5 13 0 18-5-5-5-13 0-18Z',
}
</script>

<template><svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="paths[name] || paths.chat" /></svg></template>
