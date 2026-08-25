import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import './markdown.css'

interface MarkdownProps {
  content: string
  /** 点击 doc:// 来源链接时回调 */
  onDocLink?: (docId: number) => void
}

export default function Markdown({ content, onDocLink }: MarkdownProps) {
  return (
    <div className="md-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        // 关键：默认 urlTransform 会清洗未知协议（doc:// 会被清成空 href，
        // 点击空链接 → 浏览器刷新页面）。关闭清洗，让 doc:// 保留由 onClick 拦截。
        urlTransform={(url) => url}
        components={{
          a: ({ href, children }) => (
            <a
              href={href}
              onClick={(e) => {
                if (href && href.startsWith('doc://')) {
                  e.preventDefault()
                  e.stopPropagation()
                  const id = Number(href.slice('doc://'.length))
                  if (!Number.isNaN(id)) onDocLink?.(id)
                }
              }}
            >
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
