import { useCallback, useEffect, useState } from 'react'
import {
  Button,
  Empty,
  Input,
  List,
  Popconfirm,
  Tabs,
  Typography,
  Upload,
  message,
} from 'antd'
import {
  FileTextOutlined,
  PlusOutlined,
  UploadOutlined,
  EditOutlined,
  DeleteOutlined,
  FolderOutlined,
} from '@ant-design/icons'
import axios from 'axios'
import {
  createSession,
  deleteSession,
  listDocuments,
  listLibraries,
  listSessions,
  renameSession,
  uploadDocument,
  type DocItem,
  type LibraryItem,
  type SessionItem,
} from '../api/chat'

interface LibraryPanelProps {
  currentDocId: number | null
  onSelectDoc: (id: number | null) => void
  currentLibrary: string
  onSelectLibrary: (name: string) => void
  currentSessionId: number | null
  onSelectSession: (id: number) => void
  onSessionChanged: (deletedId?: number) => void
}

/** 固定右侧操作区宽度 */
const SESSION_ACTION_W: React.CSSProperties = {
  flexShrink: 0,
  width: 56,
  textAlign: 'right',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'flex-end',
  gap: 8,
}

function DocTab({
  currentDocId,
  onSelectDoc,
  currentLibrary,
  onSelectLibrary,
}: {
  currentDocId: number | null
  onSelectDoc: (id: number | null) => void
  currentLibrary: string
  onSelectLibrary: (name: string) => void
}) {
  const [libraries, setLibraries] = useState<LibraryItem[]>([])
  const [docs, setDocs] = useState<DocItem[]>([])
  const [isAdmin, setIsAdmin] = useState(false)

  const loadDocs = useCallback(() => {
    listDocuments(currentLibrary)
      .then(setDocs)
      .catch(() => message.error('加载文档列表失败'))
  }, [currentLibrary])

  const refreshLibraries = useCallback(() => {
    listLibraries()
      .then((ls) => {
        setLibraries(ls)
        if (ls.length && !ls.some((l) => l.name === currentLibrary)) {
          onSelectLibrary(ls[0].name)
        }
      })
      .catch(() => message.error('加载资料库失败'))
  }, [currentLibrary, onSelectLibrary])

  useEffect(() => {
    refreshLibraries()
  }, [refreshLibraries])

  useEffect(() => {
    loadDocs()
  }, [loadDocs])

  useEffect(() => {
    axios
      .get('/api/health')
      .then((r) => setIsAdmin(!!r.data.is_admin))
      .catch(() => undefined)
  }, [])

  const beforeUpload = async (file: File) => {
    try {
      const r = await uploadDocument(file, currentLibrary)
      message.success(`上传成功：${r.title}（${r.chunks} 个片段）`)
      refreshLibraries()
      loadDocs()
    } catch (e: any) {
      message.error(`上传失败：${e?.response?.data?.detail || e.message}`)
    }
    return false
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 8 }}>
      {/* 资料库文件夹列表 */}
      <div style={{ flexShrink: 0 }}>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          资料库
        </Typography.Text>
        <div style={{ maxHeight: 140, overflowY: 'auto', marginTop: 4 }}>
          <List
            size="small"
            dataSource={libraries}
            locale={{ emptyText: <Empty description="暂无资料库" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
            renderItem={(lib) => (
              <List.Item
                onClick={() => onSelectLibrary(lib.name)}
                style={{ padding: '4px 6px', cursor: 'pointer', border: 'none' }}
                className={currentLibrary === lib.name ? 'panel-item-active' : 'panel-item'}
              >
                <div style={{ display: 'flex', alignItems: 'center', width: '100%', gap: 6 }}>
                  <FolderOutlined style={{ flexShrink: 0, color: 'var(--accent)' }} />
                  <Typography.Text ellipsis style={{ flex: 1, minWidth: 0 }}>
                    {lib.name}
                  </Typography.Text>
                  <Typography.Text type="secondary" style={{ fontSize: 11, flexShrink: 0 }}>
                    {lib.count}
                  </Typography.Text>
                </div>
              </List.Item>
            )}
          />
        </div>
      </div>

      {/* 当前资料库的文档 */}
      {isAdmin && (
        <Upload
          beforeUpload={beforeUpload as (file: unknown) => any}
          showUploadList={false}
          accept=".txt,.md,.pdf,.docx"
        >
          <Button className="mac-btn" icon={<UploadOutlined />} block size="small">
            上传到「{currentLibrary}」
          </Button>
        </Upload>
      )}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <List
          size="small"
          dataSource={docs}
          locale={{ emptyText: <Empty description="该资料库暂无文档" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
          renderItem={(d) => (
            <List.Item
              onClick={() => onSelectDoc(d.id)}
              style={{ padding: '5px 6px', cursor: 'pointer', border: 'none' }}
              className={currentDocId === d.id ? 'panel-item-active' : 'panel-item'}
            >
              <div style={{ display: 'flex', alignItems: 'center', width: '100%', gap: 6 }}>
                <FileTextOutlined style={{ flexShrink: 0 }} />
                <Typography.Text ellipsis style={{ flex: 1, minWidth: 0 }}>
                  {d.title}
                </Typography.Text>
              </div>
            </List.Item>
          )}
        />
      </div>
    </div>
  )
}

function SessionTab({
  currentSessionId,
  onSelectSession,
  onSessionChanged,
}: {
  currentSessionId: number | null
  onSelectSession: (id: number) => void
  onSessionChanged: (deletedId?: number) => void
}) {
  const [sessions, setSessions] = useState<SessionItem[]>([])
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editValue, setEditValue] = useState('')

  const refresh = useCallback(() => {
    listSessions('kb')
      .then(setSessions)
      .catch(() => message.error('加载会话失败'))
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  const handleNew = async () => {
    try {
      const s = await createSession('kb')
      refresh()
      onSelectSession(s.id)
    } catch {
      message.error('新建会话失败')
    }
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteSession('kb', id)
      onSessionChanged(id)
      refresh()
    } catch {
      message.error('删除会话失败')
    }
  }

  const handleRename = async (id: number) => {
    const title = editValue.trim()
    if (!title) {
      setEditingId(null)
      return
    }
    try {
      await renameSession('kb', id, title)
      message.success('已改名')
    } catch {
      message.error('改名失败')
    }
    setEditingId(null)
    refresh()
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Button className="mac-btn" icon={<PlusOutlined />} block size="small" onClick={handleNew} style={{ marginBottom: 8 }}>
        新建会话
      </Button>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        <List
          size="small"
          dataSource={sessions}
          locale={{ emptyText: <Empty description="暂无会话" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
          renderItem={(s) => (
            <List.Item
              onClick={() => onSelectSession(s.id)}
              style={{ padding: '5px 6px', cursor: 'pointer', border: 'none' }}
              className={currentSessionId === s.id ? 'panel-item-active' : 'panel-item'}
            >
              <div style={{ display: 'flex', alignItems: 'center', width: '100%', gap: 6 }}>
                {editingId === s.id ? (
                  <Input
                    size="small"
                    autoFocus
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onPressEnter={() => handleRename(s.id)}
                    onBlur={() => handleRename(s.id)}
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <>
                    <Typography.Text
                      ellipsis
                      style={{ flex: 1, minWidth: 0 }}
                      onDoubleClick={(e) => {
                        e.stopPropagation()
                        setEditingId(s.id)
                        setEditValue(s.title)
                      }}
                    >
                      {s.title}
                    </Typography.Text>
                    <div style={SESSION_ACTION_W} onClick={(e) => e.stopPropagation()}>
                      <EditOutlined
                        style={{ color: '#999', cursor: 'pointer' }}
                        onClick={() => {
                          setEditingId(s.id)
                          setEditValue(s.title)
                        }}
                      />
                      <Popconfirm title="删除该会话？" onConfirm={() => handleDelete(s.id)}>
                        <DeleteOutlined style={{ color: '#999', cursor: 'pointer' }} />
                      </Popconfirm>
                    </div>
                  </>
                )}
              </div>
            </List.Item>
          )}
        />
      </div>
    </div>
  )
}

export default function LibraryPanel({
  currentDocId,
  onSelectDoc,
  currentLibrary,
  onSelectLibrary,
  currentSessionId,
  onSelectSession,
  onSessionChanged,
}: LibraryPanelProps) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div
        style={{
          padding: '10px 14px',
          borderBottom: '1px solid var(--divider)',
          fontWeight: 600,
          fontSize: 13,
          flexShrink: 0,
        }}
      >
        资料库
      </div>
      <div style={{ flex: 1, minHeight: 0, padding: '8px 10px' }}>
        <Tabs
          size="small"
          defaultActiveKey="docs"
          items={[
            {
              key: 'docs',
              label: '文档',
              children: (
                <DocTab
                  currentDocId={currentDocId}
                  onSelectDoc={onSelectDoc}
                  currentLibrary={currentLibrary}
                  onSelectLibrary={onSelectLibrary}
                />
              ),
            },
            {
              key: 'sessions',
              label: '会话',
              children: (
                <SessionTab
                  currentSessionId={currentSessionId}
                  onSelectSession={onSelectSession}
                  onSessionChanged={onSessionChanged}
                />
              ),
            },
          ]}
          style={{ height: '100%' }}
        />
      </div>
    </div>
  )
}
