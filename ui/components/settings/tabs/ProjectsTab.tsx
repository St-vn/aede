'use client'
import React, { useState } from 'react'
import { Separator } from '@/components/ui/separator'
import { useProjects, useAddProject, useRemoveProject, useDeleteProjectFolder, useRemoveProjectRepo } from '@/hooks/useProjects'
import { FolderPicker } from '@/components/workspace/FolderPicker'
import { RemoveProjectDialog } from '@/components/workspace/RemoveProjectDialog'
import { FolderOpen, Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import type { Project } from '@/hooks/useProjects'

export function ProjectsTab() {
  const { data: projects = [] } = useProjects()
  const addProject = useAddProject()
  const removeProject = useRemoveProject()
  const deleteFolder = useDeleteProjectFolder()
  const removeGit = useRemoveProjectRepo()
  const [folderPickerOpen, setFolderPickerOpen] = useState(false)
  const [removingProject, setRemovingProject] = useState<Project | null>(null)

  const handleFolderPicked = async (path: string) => {
    await addProject.mutateAsync(path)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Projects</h3>
        <Button variant="outline" size="sm" className="text-xs" onClick={() => setFolderPickerOpen(true)}>
          <Plus className="w-3 h-3 mr-1" /> Add Project
        </Button>
      </div>
      <Separator />
      {projects.length === 0 ? (
        <p className="text-xs text-muted-foreground">No projects added yet.</p>
      ) : (
        <div className="space-y-2">
          {projects.map(p => (
            <div key={p.id} className="flex items-center gap-2 px-3 py-2 rounded-md border border-border/60">
              <FolderOpen className="w-4 h-4 text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="text-sm font-medium">{p.display_name}</span>
                <p className="text-[10px] font-mono text-muted-foreground truncate">{p.project_dir}</p>
              </div>
              <Button variant="ghost" size="icon-sm" className="h-6 w-6 text-muted-foreground hover:text-destructive shrink-0"
                onClick={() => setRemovingProject(p)}>
                <Trash2 className="w-3 h-3" />
              </Button>
            </div>
          ))}
        </div>
      )}

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
          onRemove={() => removeProject.mutate(removingProject.id)}
          onDeleteFolder={() => deleteFolder.mutate(removingProject.id)}
          onRemoveGit={() => removeGit.mutate(removingProject.id)}
        />
      )}
    </div>
  )
}
