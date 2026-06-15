'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { Menu, User, Settings, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { cn } from '@/lib/utils'
import type { NavItem } from '@/lib/docs'

interface SidebarItemProps {
  item: NavItem
  depth?: number
  pathname: string
  onNavClick?: () => void
}

function SidebarItem({ item, depth = 0, pathname, onNavClick }: SidebarItemProps) {
  const isActive = item.href ? pathname === item.href || pathname === item.href + '/' : false
  const hasChildren = item.children && item.children.length > 0

  if (hasChildren && item.children) {
    const isActiveParent = item.children.some(c =>
      c.href ? pathname === c.href || pathname === c.href + '/' : false
    )
    return (
      <Collapsible defaultOpen={depth < 2 || isActiveParent} className="group/collapsible mb-0.5">
        <CollapsibleTrigger className={cn(
          'flex items-center gap-2 w-full px-2 py-1.5 text-sm font-medium transition-colors rounded-md',
          depth === 0 ? 'text-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50',
        )}>
          <ChevronDown className="w-3.5 h-3.5 shrink-0 -rotate-90 transition-transform duration-200 data-open:rotate-0 text-muted-foreground" />
          <span className="flex-1 text-left">{item.title}</span>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <div className="ml-3">
            {item.children.map((child, i) => (
              <SidebarItem key={i} item={child} depth={depth + 1} pathname={pathname} onNavClick={onNavClick} />
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
        onClick={onNavClick}
        className={cn(
          'flex items-center gap-2 px-2 py-1.5 text-sm rounded-md transition-colors mb-0.5',
          isActive
            ? 'bg-primary/10 text-primary font-medium'
            : 'text-muted-foreground hover:text-foreground hover:bg-muted/50',
        )}
      >
        <span>{item.title}</span>
      </Link>
    )
  }

  return (
    <div className="px-2 py-1.5 text-sm font-medium text-foreground">
      {item.title}
    </div>
  )
}

interface DocsSidebarProps {
  nav: NavItem[]
  sidebarOpen?: boolean
  onToggleSidebar?: () => void
  onNavClick?: () => void
  onOpenSettings?: () => void
}

export function DocsSidebar({
  nav,
  sidebarOpen = true,
  onToggleSidebar,
  onNavClick,
  onOpenSettings,
}: DocsSidebarProps) {
  const pathname = usePathname()

  return (
    <TooltipProvider>
      <aside className={cn(
        'flex flex-col border-r border-border bg-card shrink-0 min-h-0 h-full',
        'transition-all duration-200 ease-out',
        sidebarOpen ? 'w-60' : 'w-12',
      )}>
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-3 border-b border-border h-[52px]">
          {sidebarOpen && (
            <Link href="/docs" className="text-sm font-semibold tracking-tight hover:text-primary transition-colors" onClick={onNavClick}>
              aede docs
            </Link>
          )}
          <Tooltip>
            <TooltipTrigger render={
              <Button variant="ghost" size="icon"
                aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
                onClick={onToggleSidebar}>
                <Menu className="w-4 h-4" />
              </Button>
            } />
            <TooltipContent side="right">{sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}</TooltipContent>
          </Tooltip>
        </div>

        {/* Navigation */}
        {sidebarOpen && (
          <ScrollArea className="flex-1 min-h-0 px-2">
            <div className="py-2">
              {nav.map((section, i) => (
                <SidebarItem
                  key={i}
                  item={section}
                  pathname={pathname}
                  onNavClick={onNavClick}
                />
              ))}
            </div>
          </ScrollArea>
        )}
        {!sidebarOpen && <div className="flex-1" />}

        {/* Bottom buttons */}
        <div className="flex flex-col gap-1 px-2 py-2 border-t border-border">
          {[
            { icon: <User className="w-4 h-4" />, label: 'Profile' },
            { icon: <Settings className="w-4 h-4" />, label: 'Settings', onClick: onOpenSettings },
          ].map(({ icon, label, onClick }) => (
            <Tooltip key={label}>
              <TooltipTrigger render={
                <Button variant="ghost" size="icon" aria-label={label} onClick={onClick}>{icon}</Button>
              } />
              <TooltipContent side="right">{label}</TooltipContent>
            </Tooltip>
          ))}
        </div>
      </aside>
    </TooltipProvider>
  )
}
