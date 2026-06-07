import React from 'react'
import { formatDistanceToNow } from 'date-fns'

import { MoreVertical, Trash2, Pencil } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useRenameSession } from '@/hooks/useSession'

interface Session {
  id: string; title: string; model: string; parent_id: string | null; created_at: string
}
interface Props {
  session: Session;
  isActive: boolean;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

export function SessionRow({ session, isActive, onSelect, onDelete }: Props) {
  const [mounted, setMounted] = React.useState(false)
  const [isEditing, setIsEditing] = React.useState(false)
  const [editTitle, setEditTitle] = React.useState(session.title)
  const renameMutation = useRenameSession()

  React.useEffect(() => {
    setMounted(true)
  }, [])

  React.useEffect(() => {
    setEditTitle(session.title)
  }, [session.title])

  const modelShort = session.model.split('-').slice(1, 3).join('-') || session.model // "claude-sonnet-4" → "sonnet-4"
  const relTime = mounted 
    ? formatDistanceToNow(new Date(session.created_at), { addSuffix: true })
    : ''

  const handleSave = () => {
    const trimmed = editTitle.trim()
    if (trimmed && trimmed !== session.title) {
      renameMutation.mutate({ sessionId: session.id, title: trimmed })
    }
    setIsEditing(false)
  }

  return (
    <div 
      className="relative group flex items-center rounded-md transition-all border border-transparent
                 hover:bg-accent/50 hover:border-accent-foreground/5 focus-within:bg-accent/50
                 data-[active=true]:bg-accent data-[active=true]:border-border"
      data-active={isActive}
    >
      {/* Left indicator bar for active session */}
      {isActive && (
        <div className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-md bg-primary" />
      )}
      
      {isEditing ? (
        <div className="flex-1 flex items-center gap-1.5 px-3 py-2 min-w-0">
          {session.parent_id && (
            <span className="text-muted-foreground mt-0.5 text-xs shrink-0">┆</span>
          )}
          <input
            type="text"
            className="flex-1 bg-background text-foreground border border-border rounded px-1.5 py-0.5 text-sm outline-none focus:ring-1 focus:ring-ring min-w-0"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleSave()
              } else if (e.key === 'Escape') {
                setIsEditing(false)
              }
            }}
            onBlur={handleSave}
            autoFocus
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      ) : (
        <button
          onClick={() => onSelect(session.id)}
          className="flex-1 flex items-start gap-1.5 px-3 py-2 text-left bg-transparent
                     focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1
                     focus-visible:outline-none min-w-0"
        >
          {session.parent_id && (
            <span className="text-muted-foreground mt-0.5 text-xs shrink-0">┆</span>
          )}
          <div className={`flex-1 min-w-0 ${session.parent_id ? 'ml-2' : ''} ${isActive ? 'pl-1' : ''}`}>
            <p className={`text-sm truncate pr-4 ${isActive ? 'font-semibold' : 'font-medium'} text-foreground`}>
              {session.title || 'Untitled'}
            </p>
            <p className="text-xs text-muted-foreground/80 truncate" suppressHydrationWarning>
              {mounted ? `${relTime} · ${modelShort}` : modelShort}
            </p>
          </div>
        </button>
      )}
      
      <div 
        className="px-1 opacity-0 group-hover:opacity-100 focus-within:opacity-100 group-data-[active=true]:opacity-100 transition-opacity data-[state=open]:opacity-100"
      >
        <DropdownMenu>
          <DropdownMenuTrigger render={
            <Button
              variant="ghost"
              size="icon-sm"
              className="text-muted-foreground hover:text-foreground"
              aria-label="Session actions"
            >
              <MoreVertical className="w-4 h-4" />
            </Button>
          } />
          <DropdownMenuContent align="end">
            <DropdownMenuItem 
              onClick={(e) => {
                e.stopPropagation()
                setIsEditing(true)
              }}
            >
              <Pencil className="w-4 h-4 mr-2" />
              <span>Rename</span>
            </DropdownMenuItem>
            <DropdownMenuItem 
              variant="destructive"
              onClick={(e) => {
                e.stopPropagation()
                if (confirm(`Delete session "${session.title || 'Untitled'}"?`)) {
                  onDelete(session.id)
                }
              }}
            >
              <Trash2 className="w-4 h-4 mr-2" />
              <span>Delete</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
}
