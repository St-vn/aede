'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { NavItem } from '@/lib/docs'

function SidebarItem({ item, depth = 0 }: { item: NavItem; depth?: number }) {
  const pathname = usePathname()
  const isActive = item.href ? pathname === item.href || pathname === item.href + '/' : false
  const hasChildren = item.children && item.children.length > 0

  if (hasChildren && item.children) {
    const isActiveParent = item.children.some(c =>
      c.href ? pathname === c.href || pathname === c.href + '/' : false
    )
    return (
      <Collapsible defaultOpen={depth < 2 || isActiveParent}>
        <CollapsibleTrigger className={cn(
          'flex w-full items-center gap-1 px-2 py-1.5 text-sm font-medium rounded-sm transition-colors',
          depth === 0 ? 'text-foreground' : 'text-muted-foreground',
          'hover:text-foreground hover:bg-accent',
        )}>
          <ChevronDown className="h-3 w-3 shrink-0 transition-transform ui-open:rotate-0 -rotate-90 text-muted-foreground" />
          {item.title}
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="ml-1">
            {item.children.map((child, i) => (
              <SidebarItem key={i} item={child} depth={depth + 1} />
            ))}
          </div>
        </CollapsibleContent>
      </Collapsible>
    )
  }

  if (item.href) {
    return (
      <Link
        href={item.href}
        className={cn(
          'block px-2 py-1 text-sm rounded-sm transition-colors',
          isActive
            ? 'bg-primary/10 text-primary font-medium'
            : 'text-muted-foreground hover:text-foreground hover:bg-accent',
        )}
      >
        {item.title}
      </Link>
    )
  }

  return (
    <div className="px-2 py-1 text-sm font-medium text-foreground">
      {item.title}
    </div>
  )
}

export function DocsSidebar({ nav, onNavClick }: { nav: NavItem[]; onNavClick?: () => void }) {
  return (
    <nav className="flex h-full flex-col">
      <div className="border-b border-border px-4 py-3">
        <Link
          href="/docs"
          className="text-lg font-semibold tracking-tight hover:text-primary transition-colors"
          onClick={onNavClick}
        >
          aede docs
        </Link>
      </div>
      <ScrollArea className="flex-1 px-2 py-3">
        <div className="space-y-0.5">
          {nav.map((section, i) => (
            <SidebarItem key={i} item={section} />
          ))}
        </div>
      </ScrollArea>
    </nav>
  )
}
