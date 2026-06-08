'use client'
import React, { useMemo } from 'react'
import { Command, CommandGroup, CommandItem, CommandList } from '@/components/ui/command'
import { Popover, PopoverContent } from '@/components/ui/popover'
import { useWorkspaceFiles } from '../../hooks/useWorkspaceFiles'
import { useWorkspaceInfo } from '../../hooks/useWorkspaceInfo'
import { FileCode, FileText, FolderOpen, FolderX } from 'lucide-react'

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSelect: (filename: string) => void
  searchQuery: string
  triggerRef: React.RefObject<HTMLElement | null>
}

const EMPTY_FILES: string[] = []

export function WorkspaceMentionPicker({ open, onOpenChange, onSelect, searchQuery, triggerRef }: Props) {
  const { data: files = EMPTY_FILES } = useWorkspaceFiles()
  const { data: info } = useWorkspaceInfo()

  const filtered = useMemo(() => {
    if (!searchQuery) {
      return files.slice(0, 10)
    }
    const query = searchQuery.toLowerCase()
    return files
      .filter(f => f.toLowerCase().includes(query))
      .slice(0, 10)
  }, [searchQuery, files])

  const hasFiles = files.length > 0

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverContent
        className="w-[320px] p-0 bg-popover text-popover-foreground border border-border shadow-md rounded-lg z-50"
        align="start"
        side="top"
        sideOffset={8}
        initialFocus={false}
      >
        {info && !info.has_project ? (
          <div className="flex flex-col items-center gap-2 py-6 px-4 text-center">
            <FolderX className="w-8 h-8 text-muted-foreground/50" />
            <p className="text-xs text-muted-foreground">No workspace files available</p>
            <p className="text-[11px] text-muted-foreground/60">Open a project or run <code className="text-[10px] bg-muted px-1 rounded">aede</code> from a directory with source files</p>
          </div>
        ) : !hasFiles ? (
          <div className="flex flex-col items-center gap-2 py-6 px-4 text-center">
            <FolderOpen className="w-8 h-8 text-muted-foreground/50" />
            <p className="text-xs text-muted-foreground">No matching files</p>
          </div>
        ) : (
          <Command className="bg-transparent">
            <CommandList className="max-h-[220px] overflow-y-auto p-1">
              <CommandGroup heading={info?.project_name ?? "Workspace Files"}>
                {filtered.length === 0 ? (
                  <div className="py-2 px-3 text-xs text-muted-foreground">No matching files</div>
                ) : (
                  filtered.map(file => {
                    const isCode = /\.(js|ts|tsx|py|go|rs|c|cpp|h|css|html|json)$/i.test(file)
                    return (
                      <CommandItem
                        key={file}
                        value={file}
                        onSelect={() => onSelect(file)}
                        className="flex items-center gap-2 px-3 py-1.5 text-xs cursor-pointer hover:bg-accent hover:text-accent-foreground rounded-sm"
                      >
                        {isCode ? <FileCode className="w-3.5 h-3.5 text-blue-400" /> : <FileText className="w-3.5 h-3.5 text-muted-foreground" />}
                        <span className="truncate flex-1">{file}</span>
                      </CommandItem>
                    )
                  })
                )}
              </CommandGroup>
            </CommandList>
          </Command>
        )}
      </PopoverContent>
    </Popover>
  )
}
