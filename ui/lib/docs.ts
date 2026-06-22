import fs from 'fs'
import path from 'path'
import { cache } from 'react'

const DOCS_DIR = path.join(process.cwd(), '..', 'docs')

export interface NavItem {
  title: string
  href?: string
  children?: NavItem[]
}

export interface DocPageData {
  slug: string[]
  title: string
  content: string
  frontmatter: Record<string, unknown>
}

const EXCLUDED_DIRS = new Set(['plans', 'sdlc-engineer', 'adr', 'kaizen'])

const NAV_ORDER = [
  'getting-started',
  'user-guide',
  'features',
  'architecture',
  'reference',
  'developer',
]

function parseFrontmatter(raw: string): { frontmatter: Record<string, unknown>; content: string } {
  const match = raw.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/)
  if (!match) return { frontmatter: {}, content: raw }

  const frontmatter: Record<string, unknown> = {}
  for (const line of match[1].split('\n')) {
    const idx = line.indexOf(':')
    if (idx > 0) {
      const key = line.slice(0, idx).trim()
      let value: string | string[] = line.slice(idx + 1).trim()
      if (value.startsWith('[') && value.endsWith(']')) {
        value = value.slice(1, -1).split(',').map((s: string) => s.trim().replace(/["']/g, ''))
      } else {
        value = value.replace(/["']/g, '')
      }
      frontmatter[key] = value
    }
  }
  return { frontmatter, content: match[2].trim() }
}

function extractTitle(content: string, frontmatter: Record<string, unknown>): string {
  if (frontmatter.title) return String(frontmatter.title)
  const match = content.match(/^#\s+(.+)$/m)
  return match ? match[1].trim() : 'Untitled'
}

function filePathToSlug(filePath: string): string[] {
  const relative = path.relative(DOCS_DIR, filePath)
  const parsed = path.parse(relative)
  const parts = parsed.dir ? parsed.dir.split(path.sep) : []
  if (parsed.name !== 'index') parts.push(parsed.name)
  return parts
}

function slugToFilePath(slug: string[]): string {
  if (slug.length === 0) return path.join(DOCS_DIR, 'index.md')
  const filePath = path.join(DOCS_DIR, ...slug) + '.md'
  if (fs.existsSync(filePath)) return filePath
  const indexPath = path.join(DOCS_DIR, ...slug, 'index.md')
  if (fs.existsSync(indexPath)) return indexPath
  return filePath
}

function humanize(segment: string): string {
  return segment
    .split('-')
    .map(w => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ')
}

export const getDocPage = cache((slug: string[]): DocPageData | null => {
  try {
    const filePath = slugToFilePath(slug)
    if (!fs.existsSync(filePath)) return null
    const raw = fs.readFileSync(filePath, 'utf-8')
    const { frontmatter, content } = parseFrontmatter(raw)
    const title = extractTitle(content, frontmatter)
    return { slug, title, content, frontmatter }
  } catch {
    return null
  }
})

export const getAllDocSlugs = cache((): { slug?: string[] }[] => {
  const slugs: { slug?: string[] }[] = [{}]

  function walk(dir: string) {
    const dirName = path.basename(dir)
    if (EXCLUDED_DIRS.has(dirName)) return

    const entries = fs.readdirSync(dir, { withFileTypes: true })
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name)
      if (entry.isDirectory()) {
        walk(fullPath)
      } else if (entry.name.endsWith('.md')) {
        const s = filePathToSlug(fullPath)
        if (s.length > 0) slugs.push({ slug: s })
      }
    }
  }

  walk(DOCS_DIR)
  return slugs
})

export const getDocsNav = cache((): NavItem[] => {
  const nav: NavItem[] = []

  function buildNav(dir: string): NavItem[] {
    const dirName = path.basename(dir)
    if (EXCLUDED_DIRS.has(dirName)) return []

    const items: NavItem[] = []
    const entries = fs.readdirSync(dir, { withFileTypes: true })

    const dirs = entries.filter(e => e.isDirectory() && !EXCLUDED_DIRS.has(e.name))
    for (const entry of dirs) {
      const fullPath = path.join(dir, entry.name)
      const children = buildNav(fullPath)
      const title = humanize(entry.name)

      const indexPath = path.join(fullPath, 'index.md')
      if (fs.existsSync(indexPath)) {
        const slug = filePathToSlug(indexPath)
        items.push({
          title,
          href: '/docs/' + slug.join('/'),
          children: children.length > 0 ? children : undefined,
        })
      } else if (children.length > 0) {
        items.push({ title, children })
      }
    }

    const files = entries.filter(
      e => e.isFile() && e.name.endsWith('.md') && e.name !== 'index.md',
    ).sort((a, b) => {
      const aName = path.basename(a.name, '.md').replace(/^from-/, 'from-')
      const bName = path.basename(b.name, '.md').replace(/^from-/, 'from-')
      return aName.localeCompare(bName)
    })
    for (const entry of files) {
      const fullPath = path.join(dir, entry.name)
      const slug = filePathToSlug(fullPath)
      const raw = fs.readFileSync(fullPath, 'utf-8')
      const { frontmatter, content } = parseFrontmatter(raw)
      const title = extractTitle(content, frontmatter)
      items.push({ title, href: '/docs/' + slug.join('/') })
    }

    return items
  }

  const topDirs = new Map<string, NavItem>()
  const entries = fs.readdirSync(DOCS_DIR, { withFileTypes: true })

  for (const entry of entries) {
    if (!entry.isDirectory() || EXCLUDED_DIRS.has(entry.name)) continue
    const fullPath = path.join(DOCS_DIR, entry.name)
    const children = buildNav(fullPath)
    if (children.length > 0) {
      topDirs.set(entry.name, {
        title: humanize(entry.name),
        children,
      })
    }
  }

  for (const key of NAV_ORDER) {
    if (topDirs.has(key)) {
      nav.push(topDirs.get(key)!)
      topDirs.delete(key)
    }
  }
  for (const [, item] of topDirs) {
    nav.push(item)
  }

  return nav
})

export function rewriteDocLinks(content: string): string {
  return content.replace(
    /\[([^\]]+)\]\(([^)]+)\.md\)/g,
    (_: string, text: string, link: string) => {
      if (link.startsWith('http') || link.startsWith('/')) {
        return `[${text}](${link}.md)`
      }
      const cleanPath = link.replace(/\.md$/, '')
      return `[${text}](/docs/${cleanPath})`
    },
  )
}
