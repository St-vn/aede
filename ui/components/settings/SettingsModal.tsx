'use client'
import React, { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Cog, Key, Puzzle, BarChart3, BrainCircuit, Bot, Sparkles, Keyboard, FolderOpen,
} from 'lucide-react'
import { ConfigTab } from './tabs/ConfigTab'
import { ModelsTab } from './tabs/ModelsTab'
import { McpTab } from './tabs/McpTab'
import { ContextTab } from './tabs/ContextTab'
import { MemoryTab } from './tabs/MemoryTab'
import { AgentsTab } from './tabs/AgentsTab'
import { SkillsTab } from './tabs/SkillsTab'
import { KeybindsTab } from './tabs/KeybindsTab'
import { ProjectsTab } from './tabs/ProjectsTab'
const TABS = [
  { id: 'config', label: 'Config', icon: Cog },
  { id: 'models', label: 'Models', icon: Key },
  { id: 'mcp', label: 'MCP', icon: Puzzle },
  { id: 'context', label: 'Context', icon: BarChart3 },
  { id: 'memory', label: 'Memory', icon: BrainCircuit },
  { id: 'agents', label: 'Agents', icon: Bot },
  { id: 'skills', label: 'Skills', icon: Sparkles },
  { id: 'keybinds', label: 'Keybinds', icon: Keyboard },
  { id: 'projects', label: 'Projects', icon: FolderOpen },
] as const

export type SettingsTabId = (typeof TABS)[number]['id']

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  initialTab?: SettingsTabId
}

export function SettingsModal({ open, onOpenChange, initialTab }: Props) {
  const [activeTab, setActiveTab] = useState<SettingsTabId>(initialTab || 'config')

  React.useEffect(() => {
    if (initialTab) setActiveTab(initialTab)
  }, [initialTab])

  React.useEffect(() => {
    if (open) setActiveTab(initialTab || 'config')
  }, [open, initialTab])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-4xl h-[80vh] p-0 flex flex-col overflow-hidden" aria-describedby={undefined}>
        <DialogHeader className="px-6 pt-4 pb-0">
          <DialogTitle>Settings</DialogTitle>
        </DialogHeader>
        <div className="flex-1 flex min-h-0 px-6 pb-6 gap-4">
          <Tabs
            value={activeTab}
            onValueChange={(v) => setActiveTab(v as SettingsTabId)}
            orientation="vertical"
            className="flex gap-4 w-full"
          >
            <TabsList className="flex flex-col h-full w-36 shrink-0 bg-muted/30 rounded-lg p-1 gap-0.5">
              {TABS.map(({ id, label, icon: Icon }) => (
                <TabsTrigger
                  key={id}
                  value={id}
                  className="flex items-center gap-2 w-full justify-start px-3 py-2 text-xs data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-md"
                >
                  <Icon className="w-3.5 h-3.5 shrink-0" />
                  {label}
                </TabsTrigger>
              ))}
            </TabsList>
            <ScrollArea className="flex-1 min-h-0">
              <div className="pr-2">
                <TabsContent value="config" className="mt-0">
                  <ConfigTab />
                </TabsContent>
                <TabsContent value="models" className="mt-0">
                  <ModelsTab />
                </TabsContent>
                <TabsContent value="mcp" className="mt-0">
                  <McpTab />
                </TabsContent>
                <TabsContent value="context" className="mt-0">
                  <ContextTab />
                </TabsContent>
                <TabsContent value="memory" className="mt-0">
                  <MemoryTab />
                </TabsContent>
                <TabsContent value="agents" className="mt-0">
                  <AgentsTab />
                </TabsContent>
                <TabsContent value="skills" className="mt-0">
                  <SkillsTab />
                </TabsContent>
                <TabsContent value="keybinds" className="mt-0">
                  <KeybindsTab />
                </TabsContent>
                <TabsContent value="projects" className="mt-0">
                  <ProjectsTab />
                </TabsContent>
              </div>
            </ScrollArea>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  )
}
