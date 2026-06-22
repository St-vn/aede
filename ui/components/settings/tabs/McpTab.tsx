'use client'
import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { ScopeSelector } from '@/components/settings/ScopeSelector'
import { useMcpServers, useAddMcpServer, useUpdateMcpServer, useDeleteMcpServer, useRestartMcpServers, type McpToolInfo } from '@/hooks/useMcpServers'
import { Plug, RefreshCw, Wifi, WifiOff, Plus, Trash2, X, Check, ExternalLink, Globe, ChevronRight, Code, Power, ShieldCheck } from 'lucide-react'
import { apiFetch } from '@/lib/api'

function ToolRow({ tool, disabledTools, onToggle }: {
  tool: McpToolInfo
  disabledTools: string[]
  onToggle: (toolName: string, disabled: boolean) => void
}) {
  const isDisabled = disabledTools.includes(tool.name)
  return (
    <div className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-muted/50 group">
      <Switch
        size="sm"
        checked={!isDisabled}
        onCheckedChange={(checked) => onToggle(tool.name, !checked)}
        aria-label={`toggle ${tool.name}`}
      />
      <span className="text-[11px] font-mono text-foreground flex-1">{tool.name}</span>
      <span className="text-[10px] text-muted-foreground truncate max-w-[200px]">{tool.description || ''}</span>
      {tool.inputSchema && Object.keys(tool.inputSchema).length > 0 && (
        <span className="text-[10px] text-muted-foreground/50 shrink-0" title={JSON.stringify(tool.inputSchema, null, 1)}>
          <Code className="w-3 h-3" />
        </span>
      )}
    </div>
  )
}

export function McpTab() {
  const [scope, setScope] = useState<string>('global')
  const { data: servers = {}, isLoading } = useMcpServers()
  const addServer = useAddMcpServer()
  const updateServer = useUpdateMcpServer()
  const deleteServer = useDeleteMcpServer()
  const restart = useRestartMcpServers()
  const [expandedServer, setExpandedServer] = useState<string | null>(null)

  const [showForm, setShowForm] = useState(false)
  const [newName, setNewName] = useState('')
  const [newCommand, setNewCommand] = useState('')
  const [newArgs, setNewArgs] = useState('')
  const [newUrl, setNewUrl] = useState('')
  const [newTrusted, setNewTrusted] = useState(false)
  const [useUrl, setUseUrl] = useState(false)

  const handleAdd = () => {
    if (!newName.trim()) return
    const payload: Record<string, unknown> = { name: newName.trim(), trusted: newTrusted }
    if (useUrl) {
      payload.url = newUrl.trim()
    } else {
      payload.command = newCommand.trim()
      payload.args = newArgs.trim() ? newArgs.split(/\s+/).filter(Boolean) : []
    }
    addServer.mutate(payload)
    setShowForm(false)
    setNewName('')
    setNewCommand('')
    setNewArgs('')
    setNewUrl('')
    setNewTrusted(false)
    setUseUrl(false)
  }

  const handleUpdate = (name: string, updates: Record<string, unknown>) => {
    updateServer.mutate({ name, ...updates })
  }

  const handleToolToggle = (serverName: string, currentDisabled: string[], toolName: string, disable: boolean) => {
    const newList = disable
      ? [...currentDisabled, toolName]
      : currentDisabled.filter(t => t !== toolName)
    handleUpdate(serverName, { disabled_tools: newList })
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">MCP Servers</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => apiFetch('/api/config/open', { method: 'POST', body: JSON.stringify({ scope }), headers: { 'Content-Type': 'application/json' } })}
            className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
            title="Open MCP config file in editor"
          >
            <ExternalLink className="w-3 h-3" />
            Edit file
          </button>
          <span className="text-xs text-muted-foreground">Scope:</span>
          <ScopeSelector value={scope} onChange={setScope} />
        </div>
      </div>
      <Separator />

      {!showForm && (
        <Button size="sm" className="h-7 text-xs" onClick={() => setShowForm(true)}>
          <Plus className="w-3.5 h-3.5 mr-1" /> Add MCP Server
        </Button>
      )}

      {showForm && (
        <div className="border border-border/60 rounded-lg bg-muted/30 p-3 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold">Add MCP Server</span>
            <Button variant="ghost" size="icon-sm" className="h-5 w-5 text-muted-foreground" onClick={() => { setShowForm(false); setUseUrl(false) }} aria-label="Close">
              <X className="w-3 h-3" />
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-muted-foreground">Name</label>
              <Input value={newName} onChange={e => setNewName(e.target.value)} className="h-8 text-xs" placeholder="my-server" />
            </div>
            <div className="flex items-end gap-1">
              <Button variant="ghost" size="sm" className="h-8 text-xs gap-1" onClick={() => setUseUrl(!useUrl)}>
                {useUrl ? <Globe className="w-3 h-3" /> : <Plug className="w-3 h-3" />}
                {useUrl ? 'URL mode' : 'Stdio mode'}
              </Button>
            </div>
          </div>
          {useUrl ? (
            <div className="space-y-1">
              <label className="text-[10px] font-medium text-muted-foreground">URL (SSE/WebSocket)</label>
              <Input value={newUrl} onChange={e => setNewUrl(e.target.value)} className="h-8 text-xs" placeholder="http://localhost:3002/sse" />
            </div>
          ) : (
            <>
              <div className="space-y-1">
                <label className="text-[10px] font-medium text-muted-foreground">Command</label>
                <Input value={newCommand} onChange={e => setNewCommand(e.target.value)} className="h-8 text-xs" placeholder="npx" />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-medium text-muted-foreground">Args (space-separated)</label>
                <Input value={newArgs} onChange={e => setNewArgs(e.target.value)} className="h-8 text-xs" placeholder="-y roblox-mcp" />
              </div>
            </>
          )}
          <div className="flex items-center gap-2">
            <Switch
              size="sm"
              checked={newTrusted}
              onCheckedChange={setNewTrusted}
              id="new-trusted"
            />
            <label htmlFor="new-trusted" className="text-[10px] text-muted-foreground">Trusted (bypass approval gate)</label>
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => { setShowForm(false); setUseUrl(false) }}>Cancel</Button>
            <Button size="sm" className="h-7 text-xs" onClick={handleAdd} disabled={!newName.trim() || (useUrl ? !newUrl.trim() : !newCommand.trim())}>
              <Check className="w-3 h-3 mr-1" /> Add
            </Button>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {Object.entries(servers).length === 0 && !isLoading && (
          <p className="text-xs text-muted-foreground">No MCP servers configured.</p>
        )}
        {Object.entries(servers).map(([name, server]) => {
          const isEnabled = server.enabled !== false
          const disabledTools = server.disabled_tools || []
          const tools = server.tools || []
          const isExpanded = expandedServer === name

          return (
            <div key={name} className={`rounded-md border border-border/60 ${!isEnabled ? 'opacity-50' : ''}`}>
              <div className="flex items-center gap-2 px-3 py-2">
                <button
                  className="p-0.5 rounded hover:bg-muted text-muted-foreground shrink-0"
                  onClick={() => setExpandedServer(isExpanded ? null : name)}
                  aria-label={`Expand tools for ${name}`}
                >
                  <ChevronRight className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                </button>
                <Plug className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                <div className="flex-1 min-w-0">
                  <span className="text-xs font-mono truncate block">{name}</span>
                  <span className="text-[10px] text-muted-foreground truncate block">
                    {server.url ? server.url : `${server.command} ${server.args?.join(' ') || ''}`}
                  </span>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <div className="flex items-center gap-1">
                    <Power className={`w-3 h-3 ${isEnabled ? 'text-green-500' : 'text-muted-foreground'}`} />
                    <Switch
                      size="sm"
                      checked={isEnabled}
                      onCheckedChange={(checked) => handleUpdate(name, { enabled: checked })}
                      aria-label={`enable ${name}`}
                    />
                    <span className="text-[10px] text-muted-foreground whitespace-nowrap">{isEnabled ? 'On' : 'Off'}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <ShieldCheck className={`w-3 h-3 ${server.trusted ? 'text-amber-500' : 'text-muted-foreground'}`} />
                    <Switch
                      size="sm"
                      checked={!!server.trusted}
                      onCheckedChange={(checked) => handleUpdate(name, { trusted: checked })}
                      aria-label={`trust ${name}`}
                      title={server.trusted ? 'Trusted (bypasses approval)' : 'Not trusted (requires approval)'}
                    />
                    <span className="text-[10px] text-muted-foreground whitespace-nowrap">{server.trusted ? 'Trusted' : 'Gated'}</span>
                  </div>
                </div>
                <span className="flex items-center gap-1 text-[10px] shrink-0">
                  {server.status === 'running' ? (
                    <><Wifi className="w-3 h-3 text-green-500" /> Running</>
                  ) : (
                    <><WifiOff className="w-3 h-3 text-muted-foreground" /> {server.status || 'stopped'}</>
                  )}
                </span>
                <button className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-destructive shrink-0" onClick={() => deleteServer.mutate(name)} aria-label={`Delete ${name}`}>
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>

              {isExpanded && (
                <div className="border-t border-border/40 px-3 py-2">
                  {tools.length === 0 ? (
                    <p className="text-[10px] text-muted-foreground italic">
                      {server.status === 'running' ? 'No tools reported.' : 'Start server to browse tools.'}
                    </p>
                  ) : (
                    <div className="space-y-0.5">
                      {tools.map(tool => (
                        <ToolRow
                          key={tool.name}
                          tool={tool}
                          disabledTools={disabledTools}
                          onToggle={(toolName, disable) => handleToolToggle(name, disabledTools, toolName, disable)}
                        />
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <Button variant="outline" size="sm" className="text-xs" onClick={() => restart.mutate()} disabled={restart.isPending}>
        <RefreshCw className={`w-3 h-3 mr-1 ${restart.isPending ? 'animate-spin' : ''}`} />
        Restart All
      </Button>
    </div>
  )
}
