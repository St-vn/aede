'use client'
import React, { useState } from 'react'
import { Separator } from '@/components/ui/separator'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card } from '@/components/ui/card'
import { useDaemonStatus } from '@/hooks/useDaemon'
import { apiFetch } from '@/lib/api'
import useSWR from 'swr'
import { Play, Square, Plus, Trash2, Clock, CalendarClock, RefreshCw, Loader2 } from 'lucide-react'

interface Timer {
  id: string
  delay_s: number
  action: string
  label: string
}

interface CronJob {
  id: string
  schedule: string
  action: string
  label: string
}

function DaemonTab() {
  const { data: status, error: statusError, isLoading: statusLoading, mutate: refreshStatus } = useDaemonStatus()

  const { data: timersData, mutate: refreshTimers } = useSWR<{ timers: Timer[] }>(
    () => (status?.running ? '/daemon/timers' : null),
    () => apiFetch<{ timers: Timer[] }>('/daemon/timers'),
  )

  const { data: cronData, mutate: refreshCron } = useSWR<{ jobs: CronJob[] }>(
    () => (status?.running ? '/daemon/cron' : null),
    () => apiFetch<{ jobs: CronJob[] }>('/daemon/cron'),
  )

  const [timerDelay, setTimerDelay] = useState('')
  const [timerAction, setTimerAction] = useState('')
  const [timerLabel, setTimerLabel] = useState('')
  const [addingTimer, setAddingTimer] = useState(false)

  const [cronSchedule, setCronSchedule] = useState('')
  const [cronAction, setCronAction] = useState('')
  const [cronLabel, setCronLabel] = useState('')
  const [addingCron, setAddingCron] = useState(false)
  const [cronError, setCronError] = useState<string | null>(null)

  const isRunning = status?.running ?? false

  function isValidCronExpression(expr: string): boolean {
    const trimmed = expr.trim()
    if (!trimmed) return false
    const shorthand = new Set(['@yearly', '@annually', '@monthly', '@weekly', '@daily', '@hourly', '@reboot'])
    if (shorthand.has(trimmed.toLowerCase())) return true
    const fields = trimmed.split(/\s+/)
    if (fields.length !== 5) return false
    const ranges = [
      { min: 0, max: 59 },
      { min: 0, max: 23 },
      { min: 1, max: 31 },
      { min: 1, max: 12 },
      { min: 0, max: 7 },
    ]
    return fields.every((field, i) => isValidCronField(field, ranges[i].min, ranges[i].max))
  }

  function isValidCronField(field: string, min: number, max: number): boolean {
    if (field === '*') return true
    const stepMatch = field.match(/^(.+)\/(\d+)$/)
    if (stepMatch) {
      return isValidCronFieldBase(stepMatch[1], min, max) && parseInt(stepMatch[2]) > 0
    }
    if (field.includes(',')) {
      return field.split(',').every(part => isValidCronFieldBase(part, min, max))
    }
    return isValidCronFieldBase(field, min, max)
  }

  function isValidCronFieldBase(field: string, min: number, max: number): boolean {
    const rangeMatch = field.match(/^(\d+)-(\d+)$/)
    if (rangeMatch) {
      const a = parseInt(rangeMatch[1])
      const b = parseInt(rangeMatch[2])
      return a >= min && a <= max && b >= min && b <= max && a <= b
    }
    const num = parseInt(field)
    if (!isNaN(num) && String(num) === field) {
      return num >= min && num <= max
    }
    return false
  }

  const handleStart = async () => {
    await apiFetch('/api/daemon/start', { method: 'POST' })
    await refreshStatus()
  }

  const handleStop = async () => {
    await apiFetch('/api/daemon/stop', { method: 'POST' })
    await refreshStatus()
  }

  const handleAddTimer = async () => {
    const delay = parseInt(timerDelay, 10)
    if (isNaN(delay) || delay <= 0) return
    await apiFetch('/api/daemon/timers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ delay_s: delay, action: timerAction, label: timerLabel }),
    })
    setTimerDelay('')
    setTimerAction('')
    setTimerLabel('')
    setAddingTimer(false)
    await refreshTimers()
  }

  const handleDeleteTimer = async (id: string) => {
    await apiFetch(`/api/daemon/timers/${id}`, { method: 'DELETE' })
    await refreshTimers()
  }

  const handleAddCron = async () => {
    if (!isValidCronExpression(cronSchedule)) {
      setCronError('Invalid cron expression. Use 5-field format (minute hour dom month dow) or @-shorthand.')
      return
    }
    setCronError(null)
    await apiFetch('/api/daemon/cron', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ schedule: cronSchedule, action: cronAction, label: cronLabel }),
    })
    setCronSchedule('')
    setCronAction('')
    setCronLabel('')
    setAddingCron(false)
    await refreshCron()
  }

  const handleDeleteCron = async (id: string) => {
    await apiFetch(`/api/daemon/cron/${id}`, { method: 'DELETE' })
    await refreshCron()
  }

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-medium">Daemon</h3>
      <Separator />

      <Card className="p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xs font-medium">Status:</span>
            {statusLoading ? (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <Loader2 className="w-3 h-3 animate-spin" /> Checking...
              </span>
            ) : (
              <span
                className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium ${
                  isRunning
                    ? 'bg-green-500/10 text-green-600'
                    : 'bg-muted text-muted-foreground'
                }`}
              >
                <span
                  className={`w-1.5 h-1.5 rounded-full ${
                    isRunning ? 'bg-green-500' : 'bg-muted-foreground/50'
                  }`}
                />
                {isRunning ? 'Running' : 'Stopped'}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => refreshStatus()}>
              <RefreshCw className="w-3 h-3" /> Refresh
            </Button>
            {isRunning ? (
              <Button size="sm" className="h-7 text-xs gap-1" variant="destructive" onClick={handleStop}>
                <Square className="w-3 h-3" /> Stop
              </Button>
            ) : (
              <Button size="sm" className="h-7 text-xs gap-1" onClick={handleStart}>
                <Play className="w-3 h-3" /> Start
              </Button>
            )}
          </div>
        </div>
        {isRunning && (
          <div className="mt-2 flex items-center gap-4 text-[10px] text-muted-foreground">
            {status?.pid && <span>PID: {status.pid}</span>}
            {status?.port && <span>Port: {status.port}</span>}
          </div>
        )}
        {statusError && (
          <p className="mt-2 text-[10px] text-destructive bg-destructive/10 px-2 py-1 rounded">
            {statusError.message}
          </p>
        )}
      </Card>

      {isRunning && (
        <>
          <Separator />
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-medium flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-muted-foreground" />
                Timers
              </h4>
              <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => setAddingTimer(!addingTimer)}>
                <Plus className="w-3 h-3" /> Add Timer
              </Button>
            </div>

            {addingTimer && (
              <div className="border border-border/60 rounded-lg bg-muted/30 p-3 space-y-3 mb-3">
                <div className="grid grid-cols-3 gap-2">
                  <div className="space-y-1">
                    <label className="text-[10px] font-medium text-muted-foreground">Delay (seconds)</label>
                    <Input
                      type="number"
                      min="1"
                      value={timerDelay}
                      onChange={e => setTimerDelay(e.target.value)}
                      className="h-8 text-xs"
                      placeholder="60"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-medium text-muted-foreground">Action</label>
                    <Input
                      value={timerAction}
                      onChange={e => setTimerAction(e.target.value)}
                      className="h-8 text-xs"
                      placeholder="ping"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-medium text-muted-foreground">Label</label>
                    <Input
                      value={timerLabel}
                      onChange={e => setTimerLabel(e.target.value)}
                      className="h-8 text-xs"
                      placeholder="Health check"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setAddingTimer(false)}>Cancel</Button>
                  <Button size="sm" className="h-7 text-xs" onClick={handleAddTimer} disabled={!timerDelay || !timerAction}>Add</Button>
                </div>
              </div>
            )}

            {(timersData?.timers ?? []).length === 0 ? (
              <p className="text-xs text-muted-foreground">No timers configured.</p>
            ) : (
              <div className="space-y-1">
                {(timersData?.timers ?? []).map(timer => (
                  <div key={timer.id} className="flex items-center gap-2 px-3 py-2 rounded-md border border-border/60">
                    <div className="flex-1 min-w-0">
                      <span className="text-xs font-medium">{timer.label || timer.action}</span>
                      <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                        <span>Every {timer.delay_s}s</span>
                        <span className="font-mono">{timer.action}</span>
                      </div>
                    </div>
                    <button
                      className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-destructive shrink-0"
                      onClick={() => handleDeleteTimer(timer.id)}
                      title="Delete timer"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <Separator />
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-medium flex items-center gap-1.5">
                <CalendarClock className="w-3.5 h-3.5 text-muted-foreground" />
                Cron Jobs
              </h4>
              <Button size="sm" variant="outline" className="h-7 text-xs gap-1" onClick={() => setAddingCron(!addingCron)}>
                <Plus className="w-3 h-3" /> Add Cron
              </Button>
            </div>

            {addingCron && (
              <div className="border border-border/60 rounded-lg bg-muted/30 p-3 space-y-3 mb-3">
                <div className="grid grid-cols-3 gap-2">
                  <div className="space-y-1">
                    <label className="text-[10px] font-medium text-muted-foreground">Schedule (cron expression)</label>
                    <Input
                      value={cronSchedule}
                      onChange={e => {
                        setCronSchedule(e.target.value)
                        if (cronError) setCronError(null)
                      }}
                      className="h-8 text-xs font-mono"
                      placeholder="0 9 * * *"
                    />
                    {cronError && (
                      <p className="text-[10px] text-destructive mt-1">{cronError}</p>
                    )}
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-medium text-muted-foreground">Action</label>
                    <Input
                      value={cronAction}
                      onChange={e => setCronAction(e.target.value)}
                      className="h-8 text-xs"
                      placeholder="daily_report"
                    />
                  </div>
                  <div className="space-y-1">
                    <label className="text-[10px] font-medium text-muted-foreground">Label</label>
                    <Input
                      value={cronLabel}
                      onChange={e => setCronLabel(e.target.value)}
                      className="h-8 text-xs"
                      placeholder="Morning report"
                    />
                  </div>
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={() => setAddingCron(false)}>Cancel</Button>
                  <Button size="sm" className="h-7 text-xs" onClick={handleAddCron} disabled={!cronSchedule || !cronAction}>Add</Button>
                </div>
              </div>
            )}

            {(cronData?.jobs ?? []).length === 0 ? (
              <p className="text-xs text-muted-foreground">No cron jobs configured.</p>
            ) : (
              <div className="space-y-1">
                {(cronData?.jobs ?? []).map(job => (
                  <div key={job.id} className="flex items-center gap-2 px-3 py-2 rounded-md border border-border/60">
                    <div className="flex-1 min-w-0">
                      <span className="text-xs font-medium">{job.label || job.action}</span>
                      <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                        <span className="font-mono">{job.schedule}</span>
                        <span>{job.action}</span>
                      </div>
                    </div>
                    <button
                      className="p-1 rounded hover:bg-muted text-muted-foreground hover:text-destructive shrink-0"
                      onClick={() => handleDeleteCron(job.id)}
                      title="Delete cron job"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}

export default DaemonTab
