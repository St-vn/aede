import React from 'react'

interface LayoutProps {
  sidebar: React.ReactNode
  centerPane: React.ReactNode
  rightDrawer?: React.ReactNode
}

export function Layout({ sidebar, centerPane, rightDrawer }: LayoutProps) {
  return (
    <div className="flex flex-row h-dvh overflow-hidden bg-background text-foreground">
      {sidebar}
      <main className="flex-1 flex flex-col min-w-0 min-h-0 relative overflow-hidden">{centerPane}</main>
      {rightDrawer}
    </div>
  )
}
