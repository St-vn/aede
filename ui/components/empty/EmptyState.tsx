'use client'
import React, { useState, useEffect } from 'react'
import { EMPTY_STATE } from '@/config/emptyState'
import { HeadlineRotator } from './HeadlineRotator'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import { Button } from '@/components/ui/button'
import { FolderOpen, Plus, X, BookOpen, MoreHorizontal, Trash2 } from 'lucide-react'
import { apiFetch } from '@/lib/api'
import { FolderPicker } from '@/components/workspace/FolderPicker'
import { RemoveProjectDialog } from '@/components/workspace/RemoveProjectDialog'
import { useRemoveProject, useDeleteProjectFolder, useRemoveProjectRepo } from '@/hooks/useProjects'
import type { Project } from '@/hooks/useProjects'

interface Props {
  onOpenProject?: (dir: string | null) => void
  projectName?: string
  activeProjectDir?: string | null
}

export function EmptyState({ onOpenProject, projectName, activeProjectDir }: Props) {
  const cfg = EMPTY_STATE
  const [recentProjects, setRecentProjects] = useState<Project[]>([])
  const [folderPickerOpen, setFolderPickerOpen] = useState(false)
  const [removingProject, setRemovingProject] = useState<Project | null>(null)
  const removeProject = useRemoveProject()
  const deleteFolder = useDeleteProjectFolder()
  const removeGit = useRemoveProjectRepo()

  const loadProjects = async () => {
    try {
      const projects = await apiFetch<Project[]>('/api/projects')
      setRecentProjects(projects)
    } catch { }
  }

  useEffect(() => { loadProjects() }, [])

  const handleOpenProject = async (dir: string) => {
    try {
      await apiFetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: dir }),
      })
    } catch { }
    onOpenProject?.(dir)
  }

  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 px-4">
      {cfg.image && <img src={cfg.image} alt="" className="max-h-32 opacity-80" />}
      <HeadlineRotator headlines={cfg.headlines} intervalMs={cfg.headlineIntervalMs} />
      {cfg.subtitleVisible && (
        <p className="text-sm text-muted-foreground">{cfg.subtitle}</p>
      )}

      {/* Project selector context menu */}
      <DropdownMenu>
        <DropdownMenuTrigger render={<Button variant="outline" size="lg" className="gap-2 max-w-[280px]">
          <FolderOpen className="w-4 h-4 shrink-0" />
          <span className="truncate">{projectName || 'Select Project'}</span>
          <span className="text-xs text-muted-foreground shrink-0">▼</span>
        </Button>} />
        <DropdownMenuContent align="center" className="w-64">
          <div className="max-h-60 overflow-y-auto overflow-x-hidden">
            <DropdownMenuItem onClick={() => onOpenProject?.(null)}>
              <X className="w-4 h-4 mr-2" />
              <span>No Project</span>
            </DropdownMenuItem>

            {recentProjects.length > 0 && <DropdownMenuSeparator />}

            {recentProjects.map(p => {
              const isCurrent = p.project_dir === activeProjectDir
              return (
                <div key={p.id} className={`flex items-center gap-1 rounded-md px-1.5 py-1 group ${isCurrent ? 'bg-accent' : ''}`}>
                  <button
                    onClick={() => handleOpenProject(p.project_dir)}
                    className="flex items-center gap-1.5 flex-1 min-w-0 text-left"
                  >
                    <BookOpen className="w-4 h-4 shrink-0 text-muted-foreground" />
                    <div className="flex flex-col min-w-0">
                      <span className="text-sm truncate">{p.display_name}</span>
                      <span className="text-[10px] text-muted-foreground truncate max-w-[200px]">{p.project_dir}</span>
                    </div>
                  </button>
                  <DropdownMenu>
                    <DropdownMenuTrigger render={
                      <button
                        className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-muted rounded shrink-0"
                        aria-label="Project actions"
                      >
                        <MoreHorizontal className="w-4 h-4 text-muted-foreground" />
                      </button>
                    } />
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem variant="destructive" onClick={() => setRemovingProject(p)}>
                        <Trash2 className="w-4 h-4 mr-2" />
                        <span>Delete</span>
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              )
            })}
          </div>

          <DropdownMenuSeparator />

          <DropdownMenuItem onClick={() => setFolderPickerOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            <span>Add project folder...</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <FolderPicker
        open={folderPickerOpen}
        onOpenChange={setFolderPickerOpen}
        onSelect={(path) => handleOpenProject(path)}
      />

      {removingProject && (
        <RemoveProjectDialog
          open={true}
          onOpenChange={() => setRemovingProject(null)}
          projectDir={removingProject.project_dir}
          projectName={removingProject.display_name}
          onRemove={() => { removeProject.mutate(removingProject.id); setRemovingProject(null) }}
          onDeleteFolder={() => { deleteFolder.mutate(removingProject.id); setRemovingProject(null) }}
          onRemoveGit={() => { removeGit.mutate(removingProject.id); setRemovingProject(null) }}
        />
      )}
    </div>
  )
}
