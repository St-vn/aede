'use client'

import { useState } from 'react'
import { DocsSidebar } from './sidebar'
import { MobileNav } from './mobile-nav'
import type { NavItem } from '@/lib/docs'

interface DocsLayoutClientProps {
  nav: NavItem[]
  children: React.ReactNode
}

export function DocsLayoutClient({ nav, children }: DocsLayoutClientProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="flex h-dvh">
      <div className="hidden md:block">
        <DocsSidebar
          nav={nav}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        />
      </div>
      <div className="flex flex-1 flex-col min-w-0">
        <div className="flex items-center gap-2 border-b border-border px-4 py-2 md:hidden">
          <MobileNav
            nav={nav}
            open={mobileMenuOpen}
            onOpenChange={setMobileMenuOpen}
          />
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
