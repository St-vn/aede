import { getDocsNav } from '@/lib/docs'
import { DocsSidebar } from '@/components/docs/sidebar'
import { MobileNav } from '@/components/docs/mobile-nav'
import { ScrollArea } from '@/components/ui/scroll-area'

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  const nav = getDocsNav()

  return (
    <div className="flex h-dvh">
      <div className="hidden md:block w-64 shrink-0 border-r border-border bg-card">
        <DocsSidebar nav={nav} />
      </div>
      <main className="flex flex-1 flex-col min-w-0">
        <div className="flex items-center gap-2 border-b border-border px-4 py-2 md:hidden">
          <MobileNav nav={nav} />
          <span className="font-semibold text-sm">aede docs</span>
        </div>
        <ScrollArea className="flex-1 min-h-0">
          <div className="mx-auto max-w-4xl px-6 py-8 md:py-12">
            {children}
          </div>
        </ScrollArea>
      </main>
    </div>
  )
}
