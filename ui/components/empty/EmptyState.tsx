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
import { ScrollArea } from '@/components/ui/scroll-area'
import { FolderOpen, Plus, X, BookOpen, Check } from 'lucide-react'
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

  const activeProject = recentProjects.find(p => p.project_dir === activeProjectDir)

  const loadProjects = async () => {
    try {
      const projects = await apiFetch<Project[]>('/api/projects')
      setRecentProjects(projects)
    } catch {}
  }

  useEffect(() => { loadProjects() }, [])

  const handleOpenProject = async (dir: string) => {
    try {
      await apiFetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: dir }),
      })
    } catch {}
    onOpenProject?.(dir)
  }

  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 px-4">
      {cfg.image && <img src={cfg.image} alt="" className="max-h-32 opacity-80" />}
      {projectName ? (
        <h1 className="text-2xl font-semibold text-center text-foreground">{projectName}</h1>
      ) : (
        <HeadlineRotator headlines={cfg.headlines} intervalMs={cfg.headlineIntervalMs} />
      )}
      {cfg.subtitleVisible && (
        <p className="text-sm text-muted-foreground">{cfg.subtitle}</p>
      )}

      {/* Project selector context menu */}
      <DropdownMenu>
        <DropdownMenuTrigger render={<Button variant="outline" size="lg" className="gap-2">
          <FolderOpen className="w-4 h-4" />
          {projectName ? 'Switch project' : 'Open a project'}
          <span className="text-xs text-muted-foreground">▼</span>
        </Button>} />
        <DropdownMenuContent align="center" className="w-64">
          <ScrollArea className="max-h-60">
            <DropdownMenuItem onClick={() => onOpenProject?.(null)}>
              <X className="w-4 h-4 mr-2" />
              <span>No project (chat only)</span>
            </DropdownMenuItem>

            {recentProjects.length > 0 && <DropdownMenuSeparator />}

            {recentProjects.map(p => {
              const isCurrent = p.project_dir === activeProjectDir
              return (
                <DropdownMenuItem key={p.id} onClick={() => handleOpenProject(p.project_dir)}>
                  {isCurrent ? <Check className="w-4 h-4 mr-2 text-primary" /> : <BookOpen className="w-4 h-4 mr-2" />}
                  <div className="flex flex-col flex-1 min-w-0">
                    <span className="text-sm">{p.display_name} {isCurrent && <span className="text-[10px] text-primary">(active)</span>}</span>
                    <span className="text-[10px] text-muted-foreground truncate max-w-[200px]">{p.project_dir}</span>
                  </div>
                </DropdownMenuItem>
              )
            })}
          </ScrollArea>

          <DropdownMenuSeparator />

          <DropdownMenuItem onClick={() => setFolderPickerOpen(true)}>
            <Plus className="w-4 h-4 mr-2" />
            <span>Add project folder...</span>
          </DropdownMenuItem>

          {activeProject && <DropdownMenuSeparator />}

          {activeProject && (
            <DropdownMenuItem onClick={() => setRemovingProject(activeProject)}>
              <X className="w-4 h-4 mr-2 text-destructive" />
              <span className="text-destructive">Remove "{activeProject.display_name}"</span>
            </DropdownMenuItem>
          )}
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
