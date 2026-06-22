'use client'
import React, { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { Loader2, Container } from 'lucide-react'
import { apiFetch } from '@/lib/api'

interface SandboxData {
  enabled: boolean
  image: string
  workspace_mount: string
  memory_limit: string
  cpu_limit: number
}

export function SandboxTab() {
  const [config, setConfig] = useState<SandboxData | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [enabled, setEnabled] = useState(false)
  const [image, setImage] = useState('')
  const [workspaceMount, setWorkspaceMount] = useState('')
  const [memoryLimit, setMemoryLimit] = useState('')
  const [cpuLimit, setCpuLimit] = useState('')

  useEffect(() => {
    apiFetch<{ sandbox?: SandboxData }>('/api/config')
      .then(data => {
        const s: SandboxData = data.sandbox || { enabled: false, image: 'python:3.12-slim', workspace_mount: '/workspace', memory_limit: '512m', cpu_limit: 1.0 }
        setConfig(s)
        setEnabled(s.enabled)
        setImage(s.image)
        setWorkspaceMount(s.workspace_mount)
        setMemoryLimit(s.memory_limit)
        setCpuLimit(String(s.cpu_limit))
        setLoading(false)
      })
  }, [])

  const handleSave = async () => {
    setSaving(true)
    const sandbox = {
      enabled,
      image,
      workspace_mount: workspaceMount,
      memory_limit: memoryLimit,
      cpu_limit: parseFloat(cpuLimit) || 1.0,
    }
    await apiFetch('/api/config', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: 'sandbox', value: sandbox, scope: 'global' }),
    })
    setConfig(sandbox)
    setSaving(false)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-medium">Sandboxed Execution</h3>
        <p className="text-xs text-muted-foreground">
          Run generated code in an isolated Docker container. Requires Docker Desktop to be running.
        </p>
      </div>
      <Separator />
      <div className="space-y-3">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={enabled}
            onChange={e => setEnabled(e.target.checked)}
            className="rounded border-input"
          />
          <span className="text-xs font-medium">Enable sandbox</span>
        </label>
        <div className="space-y-1.5">
          <label htmlFor="sandbox-image" className="text-xs font-medium">Docker image</label>
          <Input id="sandbox-image"
            value={image}
            onChange={e => setImage(e.target.value)}
            placeholder="python:3.12-slim"
            className="h-8 text-xs"
            disabled={!enabled}
          />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="sandbox-workspace-mount" className="text-xs font-medium">Workspace mount path</label>
          <Input id="sandbox-workspace-mount"
            value={workspaceMount}
            onChange={e => setWorkspaceMount(e.target.value)}
            placeholder="/workspace"
            className="h-8 text-xs"
            disabled={!enabled}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label htmlFor="sandbox-memory-limit" className="text-xs font-medium">Memory limit</label>
            <Input id="sandbox-memory-limit"
              value={memoryLimit}
              onChange={e => setMemoryLimit(e.target.value)}
              placeholder="512m"
              className="h-8 text-xs"
              disabled={!enabled}
            />
          </div>
          <div className="space-y-1.5">
            <label htmlFor="sandbox-cpu-limit" className="text-xs font-medium">CPU limit</label>
            <Input id="sandbox-cpu-limit"
              value={cpuLimit}
              onChange={e => setCpuLimit(e.target.value)}
              placeholder="1.0"
              className="h-8 text-xs"
              disabled={!enabled}
            />
          </div>
        </div>
        <Button size="sm" className="h-8 text-xs" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save'}
        </Button>
      </div>
      {config && config.enabled && (
        <>
          <Separator />
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Container className="w-3.5 h-3.5" />
            <span>Active sandbox: {config.image}</span>
          </div>
        </>
      )}
    </div>
  )
}
