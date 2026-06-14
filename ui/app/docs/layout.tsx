import { getDocsNav } from '@/lib/docs'
import { DocsSidebar } from '@/components/docs/sidebar'
import { MobileNav } from '@/components/docs/mobile-nav'

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  const nav = getDocsNav()

  return (
    <div className="flex h-dvh">
      <div className="hidden md:block w-64 shrink-0 border-r border-border">
        <DocsSidebar nav={nav} />
      </div>
      <div className="flex flex-1 flex-col min-w-0">
        <div className="flex items-center gap-2 border-b border-border px-4 py-2 md:hidden">
          <MobileNav nav={nav} />
          <span className="font-semibold text-sm">aede docs</span>
        </div>
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-4xl px-6 py-8 md:py-12">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}
