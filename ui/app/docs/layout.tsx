import { getDocsNav } from '@/lib/docs'
import { DocsLayoutClient } from '@/components/docs/layout-client'

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  const nav = getDocsNav()
  return <DocsLayoutClient nav={nav}>{children}</DocsLayoutClient>
}
