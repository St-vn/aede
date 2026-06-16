'use client'

import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import { Menu } from 'lucide-react'
import { DocsSidebar } from './sidebar'
import type { NavItem } from '@/lib/docs'

export function MobileNav({ nav }: { nav: NavItem[] }) {
  return (
    <Sheet>
      <SheetTrigger className="flex items-center justify-center h-8 w-8 rounded-md hover:bg-accent transition-colors">
        <Menu className="h-5 w-5" />
        <span className="sr-only">Toggle docs navigation</span>
      </SheetTrigger>
      <SheetContent side="left" className="p-0 w-64">
        <DocsSidebar nav={nav} />
      </SheetContent>
    </Sheet>
  )
}
