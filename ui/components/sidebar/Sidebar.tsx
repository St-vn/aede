'use client'
import React, { useState, useMemo } from 'react'
import { Menu, Plus, User, Settings, FolderOpen, BookOpen, MoreHorizontal, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from '@/components/ui/collapsible'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { SessionSearch } from './SessionSearch'
import { FolderPicker } from '@/components/workspace/FolderPicker'
import { RemoveProjectDialog } from '@/components/workspace/RemoveProjectDialog'
import { useProjects, useAddProject, useRemoveProject, useDeleteProjectFolder, useRemoveProjectRepo } from '@/hooks/useProjects'
import type { Project } from '@/hooks/useProjects'

interface Session {
  id: string; title: string; model: string; parent_id: string | null; created_at: string; project_dir?: string | null
}
interface SidebarProps {
  sessions: Session[]
  activeSessionId: string | null
  activeProjectDir?: string | null
  onSelectSession: (id: string) => void
  onNewSession: () => void
  onDeleteSession?: (id: string) => void
  onResumeBranch?: (id: string) => void
  onOpenProject?: (dir: string | null) => void
  onOpenSettings?: () => void
}

export function Sidebar({ sessions, activeSessionId, activeProjectDir, onSelectSession, onNewSession, onDeleteSession, onResumeBranch, onOpenProject, onOpenSettings }: SidebarProps) {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [folderPickerOpen, setFolderPickerOpen] = useState(false)
  const [removingProject, setRemovingProject] = useState<Project | null>(null)

  const { data: projects = [] } = useProjects()
  const addProject = useAddProject()
  const removeProject = useRemoveProject()
  const deleteFolder = useDeleteProjectFolder()
  const removeGit = useRemoveProjectRepo()

  const groupedByProject = useMemo(() => {
    const map = new Map<string, Session[]>()
    const noProject: Session[] = []
    for (const s of sessions) {
      const key = s.project_dir || ''
      if (key) {
        if (!map.has(key)) map.set(key, [])
        map.get(key)!.push(s)
      } else {
        noProject.push(s)
      }
    }
    return { grouped: map, noProject }
  }, [sessions])

  const handleAddProject = async () => {
    setFolderPickerOpen(true)
  }

  const handleFolderPicked = async (path: string) => {
    const project = await addProject.mutateAsync(path)
    onOpenProject?.(project.project_dir)
  }

  const handleDelete = async (id: string) => {
    onDeleteSession?.(id)
  }

  return (
    <TooltipProvider>
      <aside className={`flex flex-col border-r border-border bg-card shrink-0 min-h-0 h-full
                        transition-all duration-200 ease-out ${sidebarOpen ? 'w-60' : 'w-12'}`}>
        {/* Header */}
        <div className="flex items-center justify-between px-3 py-3 border-b border-border h-[52px]">
          {sidebarOpen && <span className="text-sm font-semibold">aede</span>}
          <Tooltip>
            <TooltipTrigger render={
              <Button variant="ghost" size="icon"
                aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
                onClick={() => setSidebarOpen(!sidebarOpen)}>
                <Menu className="w-4 h-4" />
              </Button>
            } />
            <TooltipContent side="right">{sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}</TooltipContent>
          </Tooltip>
        </div>

        {/* New Session */}
        <div className="px-2 py-2">
          <Tooltip>
            <TooltipTrigger render={
              <Button variant="ghost" size={sidebarOpen ? 'default' : 'icon'}
                aria-label="New session" onClick={onNewSession}
                className={sidebarOpen ? 'w-full justify-start gap-2' : ''}>
                <Plus className="w-4 h-4" />
                {sidebarOpen && <span>New Session</span>}
              </Button>
            } />
            {!sidebarOpen && <TooltipContent side="right">New session</TooltipContent>}
          </Tooltip>
        </div>

        {/* Project accordions */}
        {sidebarOpen && (
          <ScrollArea className="flex-1 min-h-0 px-2">
            {projects.map(project => {
              const projectSessions = groupedByProject.grouped.get(project.project_dir) || []
              const isActive = project.project_dir === activeProjectDir
              return (
                <Collapsible key={project.id} defaultOpen className="mb-1 group/project">
                  <div className={`flex items-center gap-1 rounded-md ${isActive ? 'bg-muted' : ''}`}>
                    <CollapsibleTrigger className={`flex items-center gap-2 flex-1 min-w-0 px-1 py-1.5 text-xs font-medium transition-colors rounded-md ${isActive ? 'text-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'}`}>
                      <FolderOpen className="w-3.5 h-3.5 shrink-0" />
                      <span className="truncate">{project.display_name}</span>
                      <span className="ml-auto text-[10px] text-muted-foreground/60">{projectSessions.length}</span>
                    </CollapsibleTrigger>
                    <DropdownMenu>
                      <DropdownMenuTrigger render={
                        <Button variant="ghost" size="icon-sm"
                          className="opacity-0 group-hover/project:opacity-100 transition-opacity text-muted-foreground hover:text-foreground"
                          aria-label="Project actions"
                        >
                          <MoreHorizontal className="w-3.5 h-3.5" />
                        </Button>
                      } />
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem variant="destructive" onClick={() => setRemovingProject(project)}>
                          <Trash2 className="w-4 h-4 mr-2" />
                          <span>Delete</span>
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                    <button
                      onClick={() => onOpenProject?.(project.project_dir)}
                      className="opacity-0 group-hover/project:opacity-100 transition-opacity p-1 hover:bg-muted rounded shrink-0"
                      aria-label="New session in project"
                    >
                      <Plus className="w-3.5 h-3.5 text-muted-foreground" />
                    </button>
                  </div>
                  <CollapsibleContent>
                    {projectSessions.length > 0 ? (
                      <SessionSearch sessions={projectSessions} activeId={activeSessionId} onSelect={onSelectSession} onDelete={handleDelete} onResumeBranch={onResumeBranch} />
                    ) : (
                      <p className="text-[10px] text-muted-foreground/50 px-3 py-1.5 italic">No sessions yet</p>
                    )}
                  </CollapsibleContent>
                </Collapsible>
              )
            })}

            {/* Add project button */}
            <button
              onClick={handleAddProject}
              className="flex items-center gap-2 w-full px-1 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/50 rounded transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              Add project
            </button>

            {/* No-project sessions */}
            {groupedByProject.noProject.length > 0 && (
              <Collapsible defaultOpen className="mb-1 mt-2">
                <CollapsibleTrigger className="flex items-center gap-2 w-full px-1 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors">
                  <BookOpen className="w-3.5 h-3.5 shrink-0" />
                  <span>Chats</span>
                  <span className="ml-auto text-[10px] text-muted-foreground/60">{groupedByProject.noProject.length}</span>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <SessionSearch sessions={groupedByProject.noProject} activeId={activeSessionId} onSelect={onSelectSession} onDelete={handleDelete} onResumeBranch={onResumeBranch} />
                </CollapsibleContent>
              </Collapsible>
            )}
          </ScrollArea>
        )}
        {!sidebarOpen && <div className="flex-1" />}

        {/* Bottom */}
        <div className="flex flex-col gap-1 px-2 py-2 border-t border-border">
          {[{ icon: <User className="w-4 h-4" />, label: 'Profile' },
            { icon: <Settings className="w-4 h-4" />, label: 'Settings', onClick: onOpenSettings }]
            .map(({ icon, label, onClick }) => (
              <Tooltip key={label}>
                <TooltipTrigger render={
                  <Button variant="ghost" size="icon" aria-label={label} onClick={onClick}>{icon}</Button>
                } />
                <TooltipContent side="right">{label}</TooltipContent>
              </Tooltip>
            ))}
        </div>
      </aside>

      <FolderPicker
        open={folderPickerOpen}
        onOpenChange={setFolderPickerOpen}
        onSelect={(path) => { handleFolderPicked(path); setFolderPickerOpen(false) }}
      />

      {removingProject && (
        <RemoveProjectDialog
          open={true}
          onOpenChange={() => setRemovingProject(null)}
          projectDir={removingProject.project_dir}
          projectName={removingProject.display_name}
          onRemove={() => { removeProject.mutate(removingProject.id); if (activeProjectDir === removingProject.project_dir) onOpenProject?.(null) }}
          onDeleteFolder={() => { deleteFolder.mutate(removingProject.id); if (activeProjectDir === removingProject.project_dir) onOpenProject?.(null) }}
          onRemoveGit={() => { removeGit.mutate(removingProject.id); if (activeProjectDir === removingProject.project_dir) onOpenProject?.(null) }}
        />
      )}
    </TooltipProvider>
  )
}
