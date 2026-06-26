'use client'
import React from 'react'
import { toast } from 'sonner'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { FolderOpen, Globe, Plus, MessageCircle } from 'lucide-react'
import { useProjects, useAddProject } from '@/hooks/useProjects'
import { FolderPicker } from '@/components/workspace/FolderPicker'

interface Props {
  value: string
  onChange: (scope: string) => void
}

export function ScopeSelector({ value, onChange }: Props) {
  const { data: projects = [] } = useProjects()
  const addProject = useAddProject()
  const [folderPickerOpen, setFolderPickerOpen] = React.useState(false)
  const isGlobal = value === 'global'

  const handleSelectProject = async (projectDir: string) => {
    try {
      await addProject.mutateAsync(projectDir)
    } catch {
      toast.error('Could not add project to scope')
    }
    onChange(projectDir)
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger render={
          <Button variant="outline" size="sm" className="gap-1.5 text-xs h-7" aria-label="Scope">
            {isGlobal ? (
              <Globe className="w-3.5 h-3.5 shrink-0" />
            ) : (
              <FolderOpen className="w-3.5 h-3.5 shrink-0" />
            )}
            <span className="truncate max-w-[120px]">
              {isGlobal ? 'Global' : projects.find(p => p.project_dir === value)?.display_name || value}
            </span>
            <span className="text-xs text-muted-foreground shrink-0">▼</span>
          </Button>
        } />
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuItem onClick={() => onChange('global')}>
            <Globe className="w-4 h-4 mr-2 shrink-0" />
            <span>Global</span>
            {isGlobal && <span className="ml-auto text-xs text-muted-foreground">✓</span>}
          </DropdownMenuItem>

          {projects.length > 0 && <DropdownMenuSeparator />}

          <div className="max-h-48 overflow-y-auto overflow-x-hidden">
            {projects.map(p => {
              const isSelected = p.project_dir === value
              return (
                <DropdownMenuItem key={p.id} className={isSelected ? 'bg-accent' : ''}
                  onClick={() => handleSelectProject(p.project_dir)}>
                  <MessageCircle className="w-4 h-4 mr-2 shrink-0 text-muted-foreground" />
                  <div className="flex flex-col min-w-0 flex-1">
                    <span className="text-sm truncate">{p.display_name}</span>
                    <span className="text-xs text-muted-foreground truncate max-w-[180px]">{p.project_dir}</span>
                  </div>
                  {isSelected && <span className="ml-auto text-xs text-muted-foreground shrink-0">✓</span>}
                </DropdownMenuItem>
              )
            })}
          </div>

          <DropdownMenuSeparator />

          <DropdownMenuItem onClick={() => setFolderPickerOpen(true)}>
            <Plus className="w-4 h-4 mr-2 shrink-0" />
            <span>Add project folder...</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <FolderPicker
        open={folderPickerOpen}
        onOpenChange={setFolderPickerOpen}
        onSelect={(dir) => { handleSelectProject(dir); setFolderPickerOpen(false) }}
      />
    </>
  )
}
