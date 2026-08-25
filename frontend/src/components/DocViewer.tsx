import { useEffect, useState } from 'react'
import { Empty, Spin } from 'antd'
import { getDocumentContent } from '../api/chat'
import Markdown from './Markdown'

export default function DocViewer({ docId }: { docId: number | null }) {
  const [docTitle, setDocTitle] = useState('')
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (docId == null) {
      setDocTitle('')
      setContent('')
      setError('')
      return
    }
    setLoading(true)
    setError('')
    getDocumentContent(docId)
      .then((d) => {
        setDocTitle(d.title)
        setContent(d.content)
      })
      .catch(() => setError('文档内容加载失败'))
      .finally(() => setLoading(false))
  }, [docId])

  if (docId == null) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Empty description="从左侧选择文档查看" />
      </div>
    )
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div
        style={{
          padding: '10px 16px',
          borderBottom: '1px solid var(--divider)',
          fontWeight: 600,
          fontSize: 15,
          flexShrink: 0,
        }}
      >
        {docTitle}
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '16px 24px 32px' }}>
        {loading ? (
          <Spin />
        ) : error ? (
          <div style={{ color: '#cf1322' }}>{error}</div>
        ) : (
          <Markdown content={content} />
        )}
      </div>
    </div>
  )
}
