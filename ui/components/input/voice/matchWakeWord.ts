export interface SoulData {
  name: string | null
  wake_word: string | null
  aliases: string[]
}

function levenshtein(a: string, b: string): number {
  const m = a.length, n = b.length
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0))
  for (let i = 0; i <= m; i++) dp[i][0] = i
  for (let j = 0; j <= n; j++) dp[0][j] = j
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] = a[i - 1] === b[j - 1]
        ? dp[i - 1][j - 1]
        : 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    }
  }
  return dp[m][n]
}

export function matchWakeWord(transcript: string, soul: SoulData): string | null {
  const norm = transcript.toLowerCase().replace(/[^\w\s']/g, '').trim()
  const candidates = [soul.wake_word, ...(soul.aliases || [])].filter(Boolean) as string[]
  for (const c of candidates) {
    const lc = c.toLowerCase()
    if (norm === lc) return c
    if (norm.startsWith(lc + ' ')) return c
    if (norm.endsWith(' ' + lc)) return c
    if (norm.includes(' ' + lc + ' ')) return c
  }
  // fuzzy: check first word of transcript against first word of wake word
  const firstWord = norm.split(/\s+/)[0] ?? ''
  const lastWord = norm.split(/\s+/).pop() ?? ''
  for (const c of candidates) {
    const lc = c.toLowerCase()
    const targetFirst = lc.split(/\s+/)[0] ?? ''
    const targetLast = lc.split(/\s+/).pop() ?? ''
    if (levenshtein(firstWord, targetFirst) <= 1 && targetFirst.length >= 4) return c
    if (levenshtein(lastWord, targetLast) <= 2 && targetLast.length >= 4) return c
  }
  return null
}
