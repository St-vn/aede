'use client'
import React, { useEffect, useState } from 'react'

interface Props {
  showing: boolean
  onDismiss: () => void
}

export function PermissionGate({ showing, onDismiss }: Props) {
  const [pollState, setPollState] = useState<string>('prompt')

  useEffect(() => {
    if (!showing) return
    const interval = setInterval(async () => {
      try {
        const status = await navigator.permissions.query({ name: 'microphone' as PermissionName })
        setPollState(status.state)
        if (status.state === 'granted') {
          onDismiss()
          clearInterval(interval)
        }
      } catch {
        // permissions.query not supported
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [showing, onDismiss])

  if (!showing) return null

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-destructive/10 rounded-md text-xs text-destructive" role="alert">
      <span>Microphone access blocked.</span>
      <button
        className="underline font-medium"
        onClick={() => window.open('chrome://settings/content/microphone', '_blank')}
      >
        Open site settings
      </button>
    </div>
  )
}
