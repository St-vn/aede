"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

function Label({ className, htmlFor, children, ...props }: React.ComponentProps<"label">) {
  const id = React.useId()
  const autoId = !htmlFor && React.isValidElement(children) ? id : undefined
  const child = autoId
    ? React.cloneElement(children as React.ReactElement<{ id?: string }>, { id: autoId })
    : children

  return (
    <label
      data-slot="label"
      htmlFor={autoId ?? htmlFor}
      className={cn(
        "flex items-center gap-2 text-sm leading-none font-medium select-none group-data-[disabled=true]:pointer-events-none group-data-[disabled=true]:opacity-50 peer-disabled:cursor-not-allowed peer-disabled:opacity-50",
        className
      )}
      {...props}
    >
      {child}
    </label>
  )
}

export { Label }
