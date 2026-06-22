'use client'
import React, { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Cog, Key, Plug, BarChart3, BrainCircuit, Bot, Sparkles, Keyboard, FolderOpen, Download, User, ScrollText, Server,
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
import { ImportTab } from './tabs/ImportTab'
import { SoulTab } from './tabs/SoulTab'
import { InstructionsTab } from './tabs/InstructionsTab'
import { SandboxTab } from './tabs/SandboxTab'
import DaemonTab from './tabs/DaemonTab'
const TABS = [
  { id: 'config', label: 'Config', icon: Cog },
  { id: 'models', label: 'Models', icon: Key },
  { id: 'mcp', label: 'MCP', icon: Plug },
  { id: 'context', label: 'Context', icon: BarChart3 },
  { id: 'memory', label: 'Memory', icon: BrainCircuit },
  { id: 'agents', label: 'Agents', icon: Bot },
  { id: 'skills', label: 'Skills', icon: Sparkles },
  { id: 'sandbox', label: 'Sandbox', icon: Cog },
  { id: 'keybinds', label: 'Keybinds', icon: Keyboard },
  { id: 'projects', label: 'Projects', icon: FolderOpen },
  { id: 'import', label: 'Import', icon: Download },
  { id: 'soul', label: 'Soul', icon: User },
  { id: 'daemon', label: 'Daemon', icon: Server },
  { id: 'instructions', label: 'Instructions', icon: ScrollText },
] as const

export type SettingsTabId = (typeof TABS)[number]['id']

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  initialTab?: SettingsTabId
  sessionId?: string | null
  projectDir?: string | null
}

export function SettingsModal({ open, onOpenChange, initialTab, sessionId, projectDir }: Props) {
  const [activeTab, setActiveTab] = useState<SettingsTabId>(initialTab || 'config')

  React.useEffect(() => {
    if (initialTab) setActiveTab(initialTab)
  }, [initialTab])

  React.useEffect(() => {
    if (open) setActiveTab(initialTab || 'config')
  }, [open, initialTab])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-4xl max-h-[calc(100dvh-2rem)] h-[80vh] p-0 flex flex-col overflow-hidden" aria-describedby={undefined}>
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
            <TabsList className="flex flex-col max-h-full overflow-y-auto scroll-thin w-36 shrink-0 bg-muted/30 rounded-lg p-1 gap-0.5">
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
            <ScrollArea key={activeTab} className="flex-1 min-h-0">
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
                  <ContextTab sessionId={sessionId} />
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
                <TabsContent value="sandbox" className="mt-0">
                  <SandboxTab />
                </TabsContent>
                <TabsContent value="keybinds" className="mt-0">
                  <KeybindsTab />
                </TabsContent>
                <TabsContent value="projects" className="mt-0">
                  <ProjectsTab />
                </TabsContent>
                <TabsContent value="import" className="mt-0">
                  <ImportTab />
                </TabsContent>
                <TabsContent value="soul" className="mt-0">
                  <SoulTab projectDir={projectDir} />
                </TabsContent>
                <TabsContent value="daemon" className="mt-0">
                  <DaemonTab />
                </TabsContent>
                <TabsContent value="instructions" className="mt-0">
                  <InstructionsTab projectDir={projectDir} />
                </TabsContent>
              </div>
            </ScrollArea>
          </Tabs>
        </div>
      </DialogContent>
    </Dialog>
  )
}
