'use client'
import React, { useState } from 'react'
import { Menu, Plus, User, Settings } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { ScrollArea } from '@/components/ui/scroll-area'
import { SessionSearch } from './SessionSearch'

interface Session {
  id: string; title: string; model: string; parent_id: string | null; created_at: string
}
interface SidebarProps {
  sessions: Session[]
  activeSessionId: string | null
  onSelectSession: (id: string) => void
  onNewSession: () => void
  onDeleteSession?: (id: string) => void
}

export function Sidebar({ sessions, activeSessionId, onSelectSession, onNewSession, onDeleteSession }: SidebarProps) {
  const [open, setOpen] = useState(true)

  const handleDelete = async (id: string) => {
    onDeleteSession?.(id)
  }

  return (
    <TooltipProvider>
      <aside className={`flex flex-col border-r border-border bg-card shrink-0 min-h-0 h-full
                        transition-all duration-200 ease-out ${open ? 'w-60' : 'w-12'}`}>
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-3 border-b border-border h-[52px]">
          {open && <span className="text-sm font-semibold">aede</span>}
          <Tooltip>
            <TooltipTrigger render={
              <Button variant="ghost" size="icon"
                aria-label={open ? 'Collapse sidebar' : 'Expand sidebar'}
                onClick={() => setOpen(!open)}>
                <Menu className="w-4 h-4" />
              </Button>
            } />
            <TooltipContent side="right">{open ? 'Collapse sidebar' : 'Expand sidebar'}</TooltipContent>
          </Tooltip>
        </div>

        {/* New Session */}
        <div className="px-2 py-2">
          <Tooltip>
            <TooltipTrigger render={
              <Button variant="ghost" size={open ? 'default' : 'icon'}
                aria-label="New session" onClick={onNewSession}
                className={open ? 'w-full justify-start gap-2' : ''}>
                <Plus className="w-4 h-4" />
                {open && <span>New Session</span>}
              </Button>
            } />
            {!open && <TooltipContent side="right">New session</TooltipContent>}
          </Tooltip>
        </div>

        {/* Session list */}
        {open && (
          <ScrollArea className="flex-1 min-h-0 px-2">
            {sessions.length > 0 && (
              <p className="text-xs text-muted-foreground uppercase tracking-wider px-1 py-1">Recent</p>
            )}
            <SessionSearch sessions={sessions} activeId={activeSessionId} onSelect={onSelectSession} onDelete={handleDelete} />
          </ScrollArea>
        )}
        {!open && <div className="flex-1" />}

        {/* Bottom */}
        <div className="flex flex-col gap-1 px-2 py-2 border-t border-border">
          {[{ icon: <User className="w-4 h-4" />, label: 'Profile' },
            { icon: <Settings className="w-4 h-4" />, label: 'Settings' }]
            .map(({ icon, label }) => (
              <Tooltip key={label}>
                <TooltipTrigger render={
                  <Button variant="ghost" size="icon" aria-label={label}>{icon}</Button>
                } />
                <TooltipContent side="right">{label}</TooltipContent>
              </Tooltip>
            ))}
        </div>
      </aside>
    </TooltipProvider>
  )
}
