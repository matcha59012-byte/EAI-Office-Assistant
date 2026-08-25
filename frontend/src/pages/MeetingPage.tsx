import { useCallback, useEffect, useState } from 'react'
import {
  Button,
  Empty,
  Input,
  List,
  Modal,
  Popconfirm,
  Space,
  Steps,
  Splitter,
  Tabs,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import {
  AudioOutlined,
  FileAddOutlined,
  ScanOutlined,
  ThunderboltOutlined,
  CheckOutlined,
  CloseOutlined,
  EditOutlined,
} from '@ant-design/icons'
import {
  confirmEntity,
  deleteMeetingSource,
  extractMeetingEntities,
  getMeetingSource,
  listEntities,
  listMeetingSources,
  listPending,
  scanSources,
  skipEntity,
  transcribeAudio,
  uploadMeetingSource,
  type EntityItem,
  type MeetingSource,
  type PendingItem,
} from '../api/meeting'
import Markdown from '../components/Markdown'

const STATUS_TAG: Record<string, { color: string; text: string }> = {
  ready: { color: 'blue', text: '待提取' },
  transcribing: { color: 'orange', text: '转写中' },
  pending: { color: 'purple', text: '待确认' },
  confirmed: { color: 'green', text: '已归档' },
  skipped: { color: 'default', text: '已跳过' },
}

const TYPE_LABEL: Record<string, string> = { customer: '客户/人物', project: '项目', company: '公司' }

// 每种实体可编辑的字段
const CARD_FIELDS: Record<string, { key: string; label: string }[]> = {
  customer: [
    { key: 'name', label: '姓名' }, { key: 'role', label: '角色' }, { key: 'company', label: '公司' }, { key: 'position', label: '岗位' },
    { key: 'professional_advantages', label: '专业优势' }, { key: 'career_background', label: '职业背景' },
    { key: 'personality', label: '性格' }, { key: 'hobbies', label: '爱好' }, { key: 'family', label: '家庭' }, { key: 'habits', label: '习惯' },
    { key: 'work_style', label: '做事风格' }, { key: 'decision', label: '决策风格' }, { key: 'communication', label: '沟通偏好' },
    { key: 'negotiation', label: '谈判风格' }, { key: 'goals', label: '目标计划' },
    { key: 'decision_authority', label: '决策权' }, { key: 'value_offer', label: '价值标签' }, { key: 'intelligence_priority', label: '情报优先级' },
    { key: 'level', label: '等级(A/B/C)' }, { key: 'project_views', label: '项目看法' }, { key: 'personal_ideas', label: '个人主张' },
  ],
  project: [
    { key: 'name', label: '项目名' }, { key: 'status', label: '状态' }, { key: 'background', label: '项目背景' },
    { key: 'stakeholder_map', label: '利益相关人' }, { key: 'decisions', label: '决策记录' }, { key: 'controversies', label: '争议点' },
    { key: 'budget', label: '预算' }, { key: 'timeline', label: '时间线' }, { key: 'current_phase', label: '当前阶段' }, { key: 'key_milestones', label: '关键里程碑' },
  ],
  company: [
    { key: 'name', label: '公司名' }, { key: 'region', label: '区域' }, { key: 'established', label: '成立时间' },
    { key: 'employees', label: '员工规模' }, { key: 'market_position', label: '市场定位' },
    { key: 'org_structure', label: '组织架构' }, { key: 'pipeline_ecology', label: '项目管线' }, { key: 'operation_model', label: '运营模式' },
    { key: 'pain_points', label: '痛点' }, { key: 'entry_point', label: '切入点' }, { key: 'cooperation_path', label: '合作路径' },
    { key: 'level', label: '等级(A/B/C)' },
  ],
}

function EntityCards({ items }: { items: { key: string; entity_type: string; name: string; diff?: string; card_md: string }[] }) {
  const groups: Record<string, typeof items> = { customer: [], company: [], project: [] }
  items.forEach((it) => (groups[it.entity_type] = [...(groups[it.entity_type] || []), it]))
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {(['customer', 'company', 'project'] as const).map((tp) => {
        const list = groups[tp]
        if (!list.length) return null
        return (
          <div key={tp}>
            <Typography.Text strong>{TYPE_LABEL[tp]}</Typography.Text>
            {list.map((it) => (
              <div key={it.key} style={{ background: 'rgba(255,255,255,0.5)', borderRadius: 10, padding: 10, marginTop: 6 }}>
                <Space size={6} style={{ marginBottom: 4 }}>
                  {it.diff && <Tag color={it.diff.includes('新增') ? 'green' : 'blue'}>{it.diff}</Tag>}
                  <Typography.Text strong>{it.name}</Typography.Text>
                </Space>
                <div className="entity-card-body">
                  <Markdown content={it.card_md} />
                </div>
              </div>
            ))}
          </div>
        )
      })}
    </div>
  )
}

export default function MeetingPage() {
  const [sources, setSources] = useState<MeetingSource[]>([])
  const [currentId, setCurrentId] = useState<number | null>(null)
  const [content, setContent] = useState('')
  const [filter, setFilter] = useState<string>('all')
  const [extracting, setExtracting] = useState(false)
  const [extractItems, setExtractItems] = useState<any[]>([])
  const [pending, setPending] = useState<PendingItem[]>([])
  const [entities, setEntities] = useState<EntityItem[]>([])
  const [processingId, setProcessingId] = useState<number | null>(null)
  const [editing, setEditing] = useState<PendingItem | null>(null)
  const [editForm, setEditForm] = useState<Record<string, any>>({})

  const refreshSources = useCallback(() => {
    listMeetingSources().then(setSources).catch(() => message.error('加载源文件失败'))
  }, [])
  const refreshPending = useCallback(() => {
    listPending().then(setPending).catch(() => message.error('加载待确认失败'))
  }, [])
  const refreshEntities = useCallback(() => {
    listEntities().then(setEntities).catch(() => message.error('加载实体失败'))
  }, [])

  useEffect(() => {
    refreshSources(); refreshPending(); refreshEntities()
  }, [refreshSources, refreshPending, refreshEntities])

  useEffect(() => {
    if (currentId == null) {
      setContent('')
      setExtractItems([])
      return
    }
    getMeetingSource(currentId)
      .then((d) => {
        setContent(d.content)
        if (d.status !== 'pending') setExtractItems([])
      })
      .catch(() => message.error('加载源文件失败'))
  }, [currentId])

  const handleUpload = async (file: File, isAudio: boolean) => {
    try {
      const r = isAudio ? await transcribeAudio(file) : await uploadMeetingSource(file)
      message.success(isAudio ? '音频已上传，开始转写' : '上传成功')
      refreshSources()
      setCurrentId(r.id)
    } catch (e: any) {
      message.error(`上传失败：${e?.response?.data?.detail || e.message}`)
    }
    return false
  }

  const handleScan = async () => {
    try {
      const r = await scanSources()
      message.success(`扫描完成，新增 ${r.imported} 个源文件`)
      refreshSources()
    } catch (e: any) {
      message.error(`扫描失败：${e?.response?.data?.detail || e.message}`)
    }
  }

  const handleExtract = async () => {
    if (currentId == null) {
      message.warning('请先在左侧选择一个源文件')
      return
    }
    setExtracting(true)
    try {
      const r = await extractMeetingEntities(currentId)
      setExtractItems(r.items)
      message.success(`提取完成：${r.items.length} 条实体待确认`)
      refreshSources(); refreshPending()
    } catch (e: any) {
      message.error(`提取失败：${e?.response?.data?.detail || e.message}`)
    } finally {
      setExtracting(false)
    }
  }

  const handleConfirm = async (pendingId: number) => {
    setProcessingId(pendingId)
    try {
      await confirmEntity(pendingId)
      message.success('已确认并入实体库')
      refreshPending(); refreshEntities(); refreshSources()
    } catch (e: any) {
      message.error(`确认失败：${e?.response?.data?.detail || e.message}`)
    } finally {
      setProcessingId(null)
    }
  }

  const handleSkip = async (pendingId: number) => {
    setProcessingId(pendingId)
    try {
      await skipEntity(pendingId)
      message.success('已跳过')
      refreshPending(); refreshSources()
    } catch (e: any) {
      message.error(`跳过失败：${e?.response?.data?.detail || e.message}`)
    } finally {
      setProcessingId(null)
    }
  }

  const handleConfirmAll = async () => {
    for (const item of pending) await confirmEntity(item.pending_id)
    message.success(`已全部确认（${pending.length} 条）`)
    refreshPending(); refreshEntities(); refreshSources()
  }

  const openEdit = (item: PendingItem) => {
    setEditing(item)
    setEditForm({ ...item.card })
  }

  const handleSaveEdited = async () => {
    if (!editing) return
    try {
      await confirmEntity(editing.pending_id, editForm)
      message.success('已确认并入实体库（含人工修改）')
      setEditing(null)
      refreshPending(); refreshEntities(); refreshSources()
    } catch (e: any) {
      message.error(`保存失败：${e?.response?.data?.detail || e.message}`)
    }
  }

  const handleDeleteSource = async (id: number) => {
    try {
      await deleteMeetingSource(id)
      if (currentId === id) setCurrentId(null)
      refreshSources(); refreshPending(); refreshEntities()
    } catch {
      message.error('删除失败')
    }
  }

  const filteredSources = filter === 'all' ? sources : sources.filter((s) => s.status === filter)
  const src = sources.find((s) => s.id === currentId)
  const currentStep = src ? (src.status === 'transcribing' ? 1 : src.status === 'pending' ? 3 : src.status === 'confirmed' || src.status === 'skipped' ? 4 : 2) : 0

  const pendingCards = pending.map((p) => ({ key: `p${p.pending_id}`, entity_type: p.entity_type, name: p.card.name || '未命名', card_md: p.card_md || '', tag: '待确认' }))
  const entityCards = entities.map((e) => ({ key: `e${e.id}`, entity_type: e.entity_type, name: e.name, card_md: e.card_md || '', tag: '已归档' }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, height: '100%' }}>
      {/* 步骤条 */}
      <div className="glass" style={{ padding: '6px 16px', flexShrink: 0 }}>
        <Steps
          size="small"
          current={currentStep}
          items={[
            { title: '源文件' },
            { title: '转写/上传' },
            { title: '实体提取' },
            { title: '人工确认' },
            { title: '归档知识库' },
          ]}
        />
      </div>

      {/* 三栏（可拖拽） */}
      <Splitter style={{ flex: 1, minHeight: 0 }}>
        {/* 左栏：源文件 */}
        <Splitter.Panel defaultSize="20%" min={56} max="30%" collapsible>
          <div className="glass" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--divider)', fontWeight: 600, fontSize: 13 }}>源文件</div>
            <div style={{ padding: 8, display: 'flex', flexDirection: 'column', gap: 6, flexShrink: 0 }}>
              <Upload beforeUpload={(f: any) => handleUpload(f as File, true)} showUploadList={false} accept=".mp3,.wav,.m4a,.mp4,.ogg,.flac,.mov">
                <Button className="mac-btn" icon={<AudioOutlined />} block size="small">上传音频(MP3)</Button>
              </Upload>
              <Upload beforeUpload={(f: any) => handleUpload(f as File, false)} showUploadList={false} accept=".txt,.md">
                <Button className="mac-btn" icon={<FileAddOutlined />} block size="small">上传 md/txt</Button>
              </Upload>
              <Button className="mac-btn" icon={<ScanOutlined />} block size="small" onClick={handleScan}>扫描待处理</Button>
            </div>
            <div style={{ padding: '0 8px 6px', display: 'flex', gap: 4, flexShrink: 0 }}>
              {['all', 'pending', 'confirmed'].map((f) => (
                <Button key={f} size="small" type={filter === f ? 'primary' : 'default'} onClick={() => setFilter(f)}>
                  {f === 'all' ? '全部' : f === 'pending' ? '待确认' : '已归档'}
                </Button>
              ))}
            </div>
            <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '0 8px 8px' }}>
              <List
                size="small"
                dataSource={filteredSources}
                locale={{ emptyText: <Empty description="暂无源文件" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
                renderItem={(s) => {
                  const st = STATUS_TAG[s.status] || { color: 'default', text: s.status }
                  return (
                    <List.Item
                      onClick={() => setCurrentId(s.id)}
                      style={{ padding: '5px 6px', cursor: 'pointer', border: 'none' }}
                      className={currentId === s.id ? 'panel-item-active' : 'panel-item'}
                    >
                      <div style={{ width: '100%', minWidth: 0, paddingRight: 26, position: 'relative' }}>
                        <Typography.Text ellipsis style={{ display: 'block', fontSize: 12 }}>{s.title}</Typography.Text>
                        <Tag color={st.color} style={{ fontSize: 10, marginTop: 2 }}>{st.text}</Tag>
                        <div style={{ position: 'absolute', right: 2, top: 6 }} onClick={(e) => e.stopPropagation()}>
                          <Popconfirm title="删除？" onConfirm={() => handleDeleteSource(s.id)}>
                            <span style={{ color: '#999', fontSize: 11, cursor: 'pointer' }}>删</span>
                          </Popconfirm>
                        </div>
                      </div>
                    </List.Item>
                  )
                }}
              />
            </div>
          </div>
        </Splitter.Panel>

        {/* 中栏：信息源 + 提取预览 */}
        <Splitter.Panel>
          <div className="glass" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ flex: 1, minHeight: 0, padding: '0 12px' }}>
              <Tabs
                size="small"
                style={{ height: '100%' }}
                items={[
                  {
                    key: 'doc',
                    label: '信息源文档',
                    children: (
                      <div style={{ height: '100%', overflowY: 'auto', padding: '4px 16px 16px' }}>
                        {currentId == null ? (
                          <Empty description="从左侧选择源文件查看" style={{ marginTop: 60 }} />
                        ) : content ? (
                          <Markdown content={content} />
                        ) : (
                          <Empty description="内容为空" />
                        )}
                      </div>
                    ),
                  },
                  {
                    key: 'extract',
                    label: '实体提取预览',
                    children: (
                      <div style={{ height: '100%', overflowY: 'auto', padding: '4px 12px 16px' }}>
                        <Button
                          className="mac-btn"
                          type="primary"
                          icon={<ThunderboltOutlined />}
                          loading={extracting}
                          onClick={handleExtract}
                          size="small"
                          style={{ marginBottom: 10 }}
                        >
                          对当前源文件执行提取
                        </Button>
                        {extractItems.length === 0 ? (
                          <Empty description="点击上方按钮，AI 将提取客户/项目/公司卡片" style={{ marginTop: 30 }} />
                        ) : (
                          <EntityCards items={extractItems.map((it) => ({ key: `x${it.pending_id}`, entity_type: it.entity_type, name: it.card.name || '未命名', diff: it.diff, card_md: it.card_md }))} />
                        )}
                      </div>
                    ),
                  },
                ]}
              />
            </div>
          </div>
        </Splitter.Panel>

        {/* 右栏：待确认 + 已归档 */}
        <Splitter.Panel defaultSize="28%" min={56} max="40%" collapsible>
          <div className="glass" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ flex: 1, minHeight: 0, padding: '0 12px' }}>
              <Tabs
                size="small"
                style={{ height: '100%' }}
                items={[
                  {
                    key: 'pending',
                    label: `待确认(${pending.length})`,
                    children: (
                      <div style={{ height: '100%', overflowY: 'auto', padding: '4px 4px 12px' }}>
                        {pending.length > 0 && (
                          <Button className="mac-btn" type="primary" size="small" icon={<CheckOutlined />} block onClick={handleConfirmAll} style={{ marginBottom: 8 }}>
                            全部确认
                          </Button>
                        )}
                        {pending.length === 0 ? (
                          <Empty description="暂无待确认" style={{ marginTop: 40 }} />
                        ) : (
                          pending.map((it) => (
                            <div key={it.pending_id} style={{ background: 'rgba(255,255,255,0.5)', borderRadius: 10, padding: 10, marginBottom: 8 }}>
                              <Space size={6}>
                                <Tag color="purple">{TYPE_LABEL[it.entity_type]}</Tag>
                                <Typography.Text strong>{it.card.name || '未命名'}</Typography.Text>
                              </Space>
                              <div style={{ maxHeight: 180, overflowY: 'auto', fontSize: 12, margin: '6px 0' }}>
                                <Markdown content={it.card_md || ''} />
                              </div>
                              <Space size={4}>
                                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(it)}>编辑</Button>
                                <Button size="small" type="primary" icon={<CheckOutlined />} loading={processingId === it.pending_id} onClick={() => handleConfirm(it.pending_id)}>确认</Button>
                                <Button size="small" icon={<CloseOutlined />} loading={processingId === it.pending_id} onClick={() => handleSkip(it.pending_id)}>跳过</Button>
                              </Space>
                            </div>
                          ))
                        )}
                      </div>
                    ),
                  },
                  {
                    key: 'entities',
                    label: `已归档(${entities.length})`,
                    children: (
                      <div style={{ height: '100%', overflowY: 'auto', padding: '4px 4px 12px' }}>
                        {entities.length === 0 ? (
                          <Empty description="确认后的实体归档到这里" style={{ marginTop: 40 }} />
                        ) : (
                          entityCards.map((e) => (
                            <div key={e.key} style={{ background: 'rgba(255,255,255,0.5)', borderRadius: 10, padding: 10, marginBottom: 8 }}>
                              <Tag color="green">{TYPE_LABEL[e.entity_type]}</Tag>
                              <Typography.Text strong>{e.name}</Typography.Text>
                              <div style={{ maxHeight: 220, overflowY: 'auto', fontSize: 12, marginTop: 6 }}>
                                <Markdown content={e.card_md || ''} />
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    ),
                  },
                ]}
              />
            </div>
          </div>
        </Splitter.Panel>
      </Splitter>

      {/* 编辑实体卡片弹窗 */}
      <Modal
        title={`编辑${TYPE_LABEL[editing?.entity_type || ''] || ''}卡片`}
        open={!!editing}
        onOk={handleSaveEdited}
        onCancel={() => setEditing(null)}
        width={680}
        okText="确认入库"
        cancelText="取消"
      >
        <div style={{ maxHeight: 480, overflowY: 'auto' }}>
          {editing &&
            CARD_FIELDS[editing.entity_type]?.map((f) => (
              <div key={f.key} style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 2 }}>{f.label}</div>
                {f.key === 'name' ? (
                  <Input value={editForm[f.key] || ''} onChange={(e) => setEditForm({ ...editForm, [f.key]: e.target.value })} />
                ) : (
                  <Input.TextArea rows={2} value={editForm[f.key] || ''} onChange={(e) => setEditForm({ ...editForm, [f.key]: e.target.value })} />
                )}
              </div>
            ))}
        </div>
      </Modal>
    </div>
  )
}
