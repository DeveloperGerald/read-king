import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export function MarkdownView({ markdown }: { markdown: string }) {
  return (
    <div className="prose dark:prose-invert max-w-none prose-headings:scroll-mt-24 prose-a:text-primary">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{markdown}</ReactMarkdown>
    </div>
  )
}

