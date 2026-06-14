import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import rehypeShiki from '@shikijs/rehype'

export function DocContent({ content }: { content: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[
        rehypeKatex,
        [rehypeShiki, { theme: 'github-dark' }],
      ]}
    >
      {content}
    </ReactMarkdown>
  )
}
