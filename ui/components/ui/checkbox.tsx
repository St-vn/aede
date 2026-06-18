import * as React from "react"
import { cn } from "@/lib/utils"

interface CheckboxProps extends React.ComponentProps<"input"> {
  label: string
}

function Checkbox({ className, label, id, ...props }: CheckboxProps) {
  const inputId = id || `cb-${label.replace(/\s+/g, '-').toLowerCase()}`
  return (
    <div className="flex items-center gap-2">
      <input
        type="checkbox"
        id={inputId}
        data-slot="checkbox"
        className={cn(
          "peer size-4 shrink-0 rounded-sm border border-input accent-primary",
          "focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        {...props}
      />
      <label htmlFor={inputId} className="text-sm text-foreground cursor-pointer">
        {label}
      </label>
    </div>
  )
}

export { Checkbox }
