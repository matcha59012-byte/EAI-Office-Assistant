import { useCallback, useEffect, useRef, useState } from 'react'
import { Button, Empty, Input, message } from 'antd'
import { SendOutlined } from '@ant-design/icons'
import {
  createSession,
  getMessages,
  sendMessage,
  type MessageItem,
} from '../api/chat'
import Markdown from './Markdown'

const { TextArea } = Input

interface ChatPanelProps {
  sessionScope: string
  currentSessionId: number | null
  /** 当前资料库：问答限定在该资料库内检索 */
  library?: string
  onOpenDoc: (docId: number) => void
  /** 会话变化时回调（如无会话列表时自动建会话） */
  onSessionChange?: (id: number) => void
  /** 无会话时自动创建（用于没有会话列表的模块） */
  autoCreateSession?: boolean
}

export default function ChatPanel({
  sessionScope,
  currentSessionId,
  library,
  onOpenDoc,
  onSessionChange,
  autoCreateSession,
}: ChatPanelProps) {
  const [messages, setMessages] = useState<MessageItem[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)

  const loadMessages = useCallback(
    (sid: number) => {
      getMessages(sessionScope, sid)
        .then(setMessages)
        .catch(() => message.error('加载消息失败'))
    },
    [sessionScope],
  )

  useEffect(() => {
    setMessages([])
    if (currentSessionId != null) {
      loadMessages(currentSessionId)
    } else if (autoCreateSession && onSessionChange) {
      createSession(sessionScope)
        .then((s) => onSessionChange(s.id))
        .catch(() => message.error('创建会话失败'))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentSessionId, loadMessages])

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages, sending])

  const handleSend = async () => {
    const q = input.trim()
    if (!q) return
    if (currentSessionId == null) {
      message.warning('请先在左侧"会话"页新建或选择一个会话')
      return
    }
    setInput('')
    setSending(true)
    setMessages((prev) => [...prev, { id: -Date.now(), role: 'user', content: q, created_at: '' }])
    try {
      await sendMessage(sessionScope, currentSessionId, q, null, library)
      loadMessages(currentSessionId)
    } catch (e: any) {
      message.error(`提问失败：${e?.response?.data?.detail || e.message}`)
      loadMessages(currentSessionId)
    } finally {
      setSending(false)
    }
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 面板标题 */}
      <div
        style={{
          padding: '10px 14px',
          borderBottom: '1px solid var(--divider)',
          fontWeight: 600,
          fontSize: 13,
          flexShrink: 0,
        }}
      >
        AI 问答工作台
      </div>

      {/* 消息流 */}
      <div
        ref={listRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          background: 'rgba(255,255,255,0.35)',
          borderRadius: 10,
          padding: 12,
          margin: 8,
        }}
      >
        {messages.length === 0 ? (
          <Empty
            style={{ marginTop: 60 }}
            description={currentSessionId == null ? '从左侧"会话"新建一个会话开始提问' : '开始你的提问'}
          />
        ) : (
          messages.map((m) => (
            <div
              key={m.id}
              style={{
                marginBottom: 10,
                display: 'flex',
                justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
              }}
            >
              <div
                style={{
                  maxWidth: '92%',
                  padding: '8px 12px',
                  borderRadius: 12,
                  background: m.role === 'user' ? 'rgba(10,132,255,0.85)' : 'rgba(255,255,255,0.75)',
                  color: m.role === 'user' ? '#fff' : 'var(--text-primary)',
                  border: m.role === 'assistant' ? '1px solid var(--glass-border)' : 'none',
                  backdropFilter: 'blur(12px) saturate(160%)',
                  boxShadow: '0 4px 16px rgba(0,0,0,0.04)',
                }}
              >
                {m.role === 'user' ? (
                  <div style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{m.content}</div>
                ) : (
                  <Markdown content={m.content} onDocLink={onOpenDoc} />
                )}
              </div>
            </div>
          ))
        )}
        {sending && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-secondary)', padding: '4px 0' }}>
            <span style={{ width: 14, height: 14, border: '2px solid var(--accent)', borderTopColor: 'transparent', borderRadius: '50%', display: 'inline-block', animation: 'spin 0.8s linear infinite' }} />
            AI 正在思考...
          </div>
        )}
      </div>

      {/* 输入区 */}
      <div style={{ padding: 8, flexShrink: 0 }}>
        <TextArea
          rows={3}
          placeholder="输入问题，Enter 发送，Shift+Enter 换行"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
        />
        <div style={{ marginTop: 6, textAlign: 'right' }}>
          <Button className="mac-btn" type="primary" icon={<SendOutlined />} loading={sending} onClick={handleSend}>
            发送
          </Button>
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
