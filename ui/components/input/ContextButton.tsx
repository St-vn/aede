'use client'
import React, { useRef } from 'react'
import { Plus, Paperclip, ClipboardPaste, Link } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

export interface FileAttachment {
  filename: string
  content: string
}

interface Props {
  disabled: boolean
  onAttachFile: (files: FileAttachment[]) => void
  onPasteFromClipboard: () => void
  onAddUrl: () => void
}

const ACCEPTED_EXTENSIONS = [
  '.ts', '.tsx', '.js', '.jsx', '.py', '.rs', '.go', '.java',
  '.c', '.cpp', '.h', '.css', '.scss', '.html', '.json', '.yaml',
  '.toml', '.xml', '.md', '.sql', '.sh', '.bash', '.ps1',
  '.txt', '.log', '.csv', '.env', '.cfg', '.ini',
]

export function ContextButton({ disabled, onAttachFile, onPasteFromClipboard, onAddUrl }: Props) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleAttachFile = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const fileList = e.target.files
    if (!fileList || fileList.length === 0) return

    const results: FileAttachment[] = []
    for (const file of Array.from(fileList)) {
      const content = await file.text()
      results.push({ filename: file.name, content })
    }
    onAttachFile(results)
    e.target.value = ''
  }

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        multiple
        className="hidden"
        onChange={handleFileChange}
        accept={ACCEPTED_EXTENSIONS.join(',')}
      />
      <DropdownMenu>
        <DropdownMenuTrigger render={
          <Button variant="ghost" size="icon" className="w-7 h-7" aria-label="Add context" disabled={disabled}>
            <Plus className="w-4 h-4" />
          </Button>
        } />
        <DropdownMenuContent align="start">
          <DropdownMenuItem onClick={handleAttachFile}>
            <Paperclip className="w-4 h-4 mr-2" />
            <span>Attach file</span>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={onPasteFromClipboard}>
            <ClipboardPaste className="w-4 h-4 mr-2" />
            <span>Paste from clipboard</span>
          </DropdownMenuItem>
          <DropdownMenuItem onClick={onAddUrl}>
            <Link className="w-4 h-4 mr-2" />
            <span>Add URL</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </>
  )
}
