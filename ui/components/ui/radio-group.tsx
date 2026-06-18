import * as React from "react"
import { cn } from "@/lib/utils"

function RadioGroup({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="radio-group"
      role="radiogroup"
      className={cn("grid gap-2", className)}
      {...props}
    />
  )
}

interface RadioGroupItemProps extends React.ComponentProps<"input"> {
  label: string
}

function RadioGroupItem({ className, label, id, ...props }: RadioGroupItemProps) {
  const inputId = id || `radio-${label.replace(/\s+/g, '-').toLowerCase()}`
  return (
    <div className="flex items-center gap-2">
      <input
        type="radio"
        id={inputId}
        data-slot="radio-group-item"
        className={cn(
          "peer size-4 shrink-0 rounded-full border border-input accent-primary",
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

export { RadioGroup, RadioGroupItem }
