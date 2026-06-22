import { getDocPage, getAllDocSlugs, rewriteDocLinks } from '@/lib/docs'
import { DocContent } from '@/components/docs/doc-content'
import { notFound } from 'next/navigation'

export function generateStaticParams() {
  return getAllDocSlugs()
}

export default async function DocPage({
  params,
}: {
  params: Promise<{ slug?: string[] }>
}) {
  const { slug } = await params
  const page = getDocPage(slug ?? [])
  if (!page) notFound()

  const content = rewriteDocLinks(page.content)

  return (
    <article className="docs-content">
      <DocContent content={content} />
    </article>
  )
}
