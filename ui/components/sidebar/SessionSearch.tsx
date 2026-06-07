'use client'
import React, { useState } from 'react'
import { Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { SessionRow } from './SessionRow'

interface Session { id: string; title: string; model: string; parent_id: string | null; created_at: string }
interface Props { sessions: Session[]; onSelect: (id: string) => void; onDelete: (id: string) => void; activeId?: string | null }

export function SessionSearch({ sessions, onSelect, onDelete, activeId }: Props) {
  const [query, setQuery] = useState('')
  const filtered = query
    ? sessions.filter(s => (s.title || 'Untitled').toLowerCase().includes(query.toLowerCase()))
    : sessions

  return (
    <div className="flex flex-col gap-1">
      <div className="relative px-2 py-1">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground pointer-events-none" />
        <Input
          type="search"
          role="searchbox"
          placeholder="Search sessions..."
          aria-label="Search sessions"
          value={query}
          onChange={e => setQuery(e.target.value)}
          className="pl-8 h-8 text-xs bg-transparent border-border"
        />
      </div>
      <div className="space-y-0.5 px-2">
        {filtered.map(s => (
          <SessionRow key={s.id} session={s} isActive={s.id === activeId} onSelect={onSelect} onDelete={onDelete} />
        ))}
      </div>
    </div>
  )
}
