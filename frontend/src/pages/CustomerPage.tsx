import { useCallback, useEffect, useState } from 'react'
import {
  Button,
  Dropdown,
  Empty,
  Input,
  List,
  Modal,
  Popconfirm,
  Progress,
  Space,
  Splitter,
  Tabs,
  Tag,
  Typography,
  Upload,
  message,
} from 'antd'
import {
  SearchOutlined,
  UploadOutlined,
  EditOutlined,
  DeleteOutlined,
  AlertOutlined,
  DownOutlined,
} from '@ant-design/icons'
import MDEditor from '@uiw/react-md-editor'
import '@uiw/react-md-editor/markdown-editor.css'
import {
  askEntity,
  customerAlerts,
  customerDashboard,
  deleteCustomerEntity,
  followCustomerEntity,
  getCustomerEntity,
  importCustomers,
  listCustomerEntities,
  updateCustomerEntity,
  type CustomerEntity,
  type Dashboard,
} from '../api/customer'
import Markdown from '../components/Markdown'

const TYPE_LABEL: Record<string, string> = { customer: '客户', project: '项目', company: '公司' }
const STATUS_COLOR: Record<string, string> = { 新: 'blue', 跟进中: 'green', 静默: 'orange', 已关闭: 'default' }
const STATUSES = ['新', '跟进中', '静默', '已关闭']

/* iOS 玻璃分段控件 */
function Segmented({ options, value, onChange }: { options: { value: string; label: string }[]; value: string; onChange: (v: string) => void }) {
  return (
    <div style={{ display: 'flex', background: 'rgba(255,255,255,0.4)', borderRadius: 999, padding: 3, gap: 2 }}>
      {options.map((o) => (
        <div
          key={o.value}
          onClick={() => onChange(o.value)}
          style={{
            flex: 1, textAlign: 'center', padding: '4px 0', borderRadius: 999, fontSize: 12, cursor: 'pointer',
            background: value === o.value ? 'rgba(255,255,255,0.92)' : 'transparent',
            boxShadow: value === o.value ? '0 1px 4px rgba(0,0,0,0.12)' : 'none',
            color: value === o.value ? '#1d1d1f' : '#6e6e73',
            transition: 'all .2s',
          }}
        >
          {o.label}
        </div>
      ))}
    </div>
  )
}

/* 计算项目进度（按当前日期） */
function projectProgress(card: Record<string, any>) {
  const s = String(card.start_date || '').trim()
  const e = String(card.end_date_est || card.end_date || '').trim()
  const today = new Date()
  const parse = (v: string) => new Date(v)
  if (!s || !e) return { ok: false }
  const start = parse(s); const end = parse(e)
  if (isNaN(start.getTime()) || isNaN(end.getTime())) return { ok: false }
  const total = Math.max(1, end.getTime() - start.getTime())
  if (today < start) return { ok: true, pct: 0, label: '未开始', color: 'default', s, e }
  if (today > end) return { ok: true, pct: 100, label: '已到/超过完工时间', color: today > end ? 'orange' : 'success', s, e }
  const pct = Math.round(((today.getTime() - start.getTime()) / total) * 100)
  return { ok: true, pct, label: `进行中 ${pct}%`, color: 'blue', s, e }
}

export default function CustomerPage() {
  const [list, setList] = useState<CustomerEntity[]>([])
  const [type, setType] = useState<string>('customer')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [search, setSearch] = useState('')
  const [currentId, setCurrentId] = useState<number | null>(null)
  const [detail, setDetail] = useState<CustomerEntity | null>(null)
  const [dash, setDash] = useState<Dashboard | null>(null)
  const [alerts, setAlerts] = useState<any[]>([])
  const [projects, setProjects] = useState<CustomerEntity[]>([])

  // 编辑 md
  const [editing, setEditing] = useState<CustomerEntity | null>(null)
  const [mdValue, setMdValue] = useState('')
  const [dirty, setDirty] = useState(false)

  // 实体问答
  const [askQ, setAskQ] = useState('')
  const [askResult, setAskResult] = useState<{ answer: string; sources: { id: number; type: string; name: string }[] } | null>(null)
  const [asking, setAsking] = useState(false)

  const refreshList = useCallback(() => {
    listCustomerEntities(type, statusFilter || undefined, search || undefined).then(setList).catch(() => message.error('加载列表失败'))
  }, [type, statusFilter, search])

  const refreshDash = useCallback(() => {
    customerDashboard().then(setDash).catch(() => undefined)
    customerAlerts().then(setAlerts).catch(() => undefined)
    listCustomerEntities('project').then(setProjects).catch(() => undefined)
  }, [])

  useEffect(() => { refreshList() }, [refreshList])
  useEffect(() => { refreshDash() }, [refreshDash])
  useEffect(() => {
    if (currentId == null) { setDetail(null); return }
    getCustomerEntity(currentId).then(setDetail).catch(() => message.error('加载详情失败'))
  }, [currentId])

  const handleImport = async (file: File) => {
    try {
      const r = await importCustomers(file)
      message.success(`导入 ${r.imported}，跳过 ${r.skipped}`)
      refreshList(); refreshDash()
    } catch (e: any) {
      message.error(`导入失败：${e?.response?.data?.detail || e.message}`)
    }
    return false
  }

  const handleStatusChange = async (status: string) => {
    if (!detail || status === detail.status) return
    try {
      await followCustomerEntity(detail.id, status)
      message.success(`状态 → ${status}`)
      getCustomerEntity(detail.id).then(setDetail)
      refreshList(); refreshDash()
    } catch {
      message.error('状态更新失败')
    }
  }

  const openEdit = (item: CustomerEntity) => {
    setEditing(item)
    setMdValue(item.card_md || '')
    setDirty(false)
  }

  const handleSaveMd = async () => {
    if (!editing) return
    try {
      await updateCustomerEntity(editing.id, { card_md: mdValue })
      message.success('已保存')
      setEditing(null); setDirty(false)
      if (currentId) getCustomerEntity(currentId).then(setDetail)
      refreshList()
    } catch (e: any) {
      message.error(`保存失败：${e?.response?.data?.detail || e.message}`)
    }
  }

  const handleCloseEdit = () => {
    if (!dirty) { setEditing(null); return }
    Modal.confirm({
      title: '有未保存的修改',
      content: '是否保存本次编辑？',
      okText: '保存',
      cancelText: '放弃',
      onOk: handleSaveMd,
      onCancel: () => setEditing(null),
    })
  }

  const handleDelete = async (id: number) => {
    try {
      await deleteCustomerEntity(id)
      message.success('已删除')
      if (currentId === id) setCurrentId(null)
      refreshList(); refreshDash()
    } catch {
      message.error('删除失败')
    }
  }

  const handleAsk = async () => {
    if (!askQ.trim()) { message.warning('请输入问题'); return }
    setAsking(true); setAskResult(null)
    try {
      const r = await askEntity(askQ)
      setAskResult(r)
    } catch (e: any) {
      message.error(`问答失败：${e?.response?.data?.detail || e.message}`)
    } finally {
      setAsking(false)
    }
  }

  const timeline = projects.map((p) => ({ p, prog: projectProgress(p.card || {}) })).filter((x) => x.prog.ok)

  return (
    <Splitter style={{ height: '100%' }}>
      {/* 左栏 */}
      <Splitter.Panel defaultSize="18%" min={56} max="30%" collapsible>
        <div className="glass" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--divider)', fontWeight: 600, fontSize: 13 }}>实体库</div>
          <div style={{ padding: 10, display: 'flex', flexDirection: 'column', gap: 8, flexShrink: 0 }}>
            <Segmented
              options={[{ value: 'customer', label: '客户' }, { value: 'company', label: '公司' }, { value: 'project', label: '项目' }]}
              value={type}
              onChange={(v) => { setType(v); setCurrentId(null) }}
            />
            <Segmented
              options={[{ value: '', label: '全部' }, ...STATUSES.map((s) => ({ value: s, label: s }))]}
              value={statusFilter}
              onChange={setStatusFilter}
            />
            <Input prefix={<SearchOutlined />} placeholder="搜索" value={search} onChange={(e) => setSearch(e.target.value)} allowClear size="small" />
            <Space>
              <Upload beforeUpload={(f: any) => handleImport(f as File)} showUploadList={false} accept=".xlsx,.xls">
                <Button className="mac-btn" icon={<UploadOutlined />} size="small">导入Excel</Button>
              </Upload>
            </Space>
          </div>
          <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '0 8px 8px' }}>
            <List
              size="small"
              dataSource={list}
              locale={{ emptyText: <Empty description="暂无数据" image={Empty.PRESENTED_IMAGE_SIMPLE} /> }}
              renderItem={(e) => (
                <List.Item
                  onClick={() => setCurrentId(e.id)}
                  style={{ padding: '5px 6px', cursor: 'pointer', border: 'none' }}
                  className={currentId === e.id ? 'panel-item-active' : 'panel-item'}
                >
                  <div style={{ width: '100%', minWidth: 0, paddingRight: 26, position: 'relative' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Typography.Text ellipsis style={{ flex: 1, minWidth: 0, fontSize: 12 }}>{e.name}</Typography.Text>
                      {e.status === '静默' && <span style={{ color: '#ff4d4f' }}>🔴</span>}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{e.card?.company || e.card?.market_position || ''}</div>
                    <Tag color={STATUS_COLOR[e.status] || 'default'} style={{ fontSize: 10, marginTop: 2 }}>{e.status}</Tag>
                    <div style={{ position: 'absolute', right: 2, top: 6 }} onClick={(ev) => ev.stopPropagation()}>
                      <Popconfirm title="删除？" onConfirm={() => handleDelete(e.id)}>
                        <span style={{ color: '#999', fontSize: 11, cursor: 'pointer' }}>删</span>
                      </Popconfirm>
                    </div>
                  </div>
                </List.Item>
              )}
            />
          </div>
        </div>
      </Splitter.Panel>

      {/* 中栏：实体信息详情 */}
      <Splitter.Panel>
        <div className="glass" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--divider)', fontWeight: 600, fontSize: 13, display: 'flex', alignItems: 'center', gap: 8 }}>
            实体信息详情
            {detail && (
              <Space size={4}>
                <Dropdown
                  menu={{
                    items: [...STATUSES.map((s) => ({ key: s, label: s })), { key: 'cancel', label: '取消', disabled: true }],
                    onClick: ({ key }) => handleStatusChange(key),
                  }}
                  trigger={['click']}
                >
                  <Button size="small" icon={<DownOutlined />}>
                    状态：{detail.status}
                  </Button>
                </Dropdown>
                <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(detail)}>编辑</Button>
              </Space>
            )}
          </div>
          <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '12px 20px 24px' }}>
            {detail == null ? (
              <Empty description="从左侧选择实体查看详情" style={{ marginTop: 80 }} />
            ) : (
              <Markdown content={detail.card_md || ''} />
            )}
          </div>
        </div>
      </Splitter.Panel>

      {/* 右栏：看板 / 时间轴 / 实体问答 */}
      <Splitter.Panel defaultSize="30%" min={56} max="40%" collapsible>
        <div className="glass" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <div style={{ flex: 1, minHeight: 0, padding: '0 12px' }}>
            <Tabs
              size="small"
              style={{ height: '100%' }}
              items={[
                {
                  key: 'dash',
                  label: '看板',
                  children: (
                    <div style={{ height: '100%', overflowY: 'auto', padding: '4px 4px 12px' }}>
                      {dash && (
                        <div>
                          <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
                            {[
                              { label: '客户', value: dash.customers, color: '#0a84ff' },
                              { label: '公司', value: dash.companies, color: '#30d158' },
                              { label: '项目', value: dash.projects, color: '#ff9f0a' },
                            ].map((c) => (
                              <div key={c.label} style={{ flex: 1, background: 'rgba(255,255,255,0.5)', borderRadius: 12, padding: 12, textAlign: 'center' }}>
                                <div style={{ fontSize: 24, fontWeight: 700, color: c.color }}>{c.value}</div>
                                <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{c.label}</div>
                              </div>
                            ))}
                          </div>
                          <div style={{ background: 'rgba(255,255,255,0.5)', borderRadius: 12, padding: 12 }}>
                            <Typography.Text strong style={{ fontSize: 12 }}>客户状态分布</Typography.Text>
                            {Object.entries(dash.status_dist || {}).map(([k, v]) => (
                              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginTop: 4 }}>
                                <span>{k}</span><span>{String(v)}</span>
                              </div>
                            ))}
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginTop: 6, color: '#ff4d4f' }}>
                              <span>🔴 静默</span><span>{dash.silent}</span>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ),
                },
                {
                  key: 'timeline',
                  label: `项目时间轴(${timeline.length})`,
                  children: (
                    <div style={{ height: '100%', overflowY: 'auto', padding: '4px 4px 12px' }}>
                      {timeline.length === 0 ? (
                        <Empty description="暂无项目时间数据（需提取 start/end 日期）" style={{ marginTop: 40 }} />
                      ) : (
                        timeline.map(({ p, prog }) => (
                          <div key={p.id} onClick={() => { setType('project'); setCurrentId(p.id) }} style={{ background: 'rgba(255,255,255,0.5)', borderRadius: 10, padding: 10, marginBottom: 8, cursor: 'pointer' }}>
                            <Typography.Text strong>{p.name}</Typography.Text>
                            <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
                              {prog!.s} → {prog!.e} ｜ {prog!.label}
                            </div>
                            <Progress percent={prog!.pct} size="small" strokeColor={prog!.color === 'blue' ? '#0a84ff' : prog!.color === 'orange' ? '#ff9f0a' : '#30d158'} showInfo={false} style={{ marginTop: 4 }} />
                          </div>
                        ))
                      )}
                    </div>
                  ),
                },
                {
                  key: 'ask',
                  label: '实体问答',
                  children: (
                    <div style={{ height: '100%', overflowY: 'auto', padding: '4px 4px 12px' }}>
                      <Input.TextArea rows={2} placeholder='例如："张三什么情况？"' value={askQ} onChange={(e) => setAskQ(e.target.value)} />
                      <Button className="mac-btn" type="primary" size="small" style={{ marginTop: 6 }} loading={asking} onClick={handleAsk}>提问</Button>
                      {askResult && (
                        <div style={{ marginTop: 10 }}>
                          <div style={{ background: 'rgba(255,255,255,0.5)', borderRadius: 10, padding: 10 }}>
                            <Markdown content={askResult.answer} />
                          </div>
                          {askResult.sources.length > 0 && (
                            <div style={{ marginTop: 6 }}>
                              <Typography.Text strong style={{ fontSize: 12 }}>来源</Typography.Text>
                              {askResult.sources.map((s) => (
                                <div key={s.id} onClick={() => { setType(s.type); setCurrentId(s.id) }} style={{ fontSize: 12, color: '#1677ff', cursor: 'pointer', marginTop: 2 }}>
                                  [{TYPE_LABEL[s.type] || s.type}] {s.name}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ),
                },
              ]}
            />
          </div>
        </div>
      </Splitter.Panel>

      {/* 二级编辑窗口：macOS 风格，覆盖全屏，居中弹出 */}
      {editing && (
        <div
          style={{
            position: 'fixed', inset: 0, zIndex: 2000,
            background: 'rgba(0,0,0,0.35)', backdropFilter: 'blur(10px)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            animation: 'eaiFadeIn .2s ease',
          }}
          onClick={handleCloseEdit}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              width: 'min(780px, 92vw)', maxHeight: '84vh',
              display: 'flex', flexDirection: 'column', overflow: 'hidden',
              background: 'rgba(249,249,252,0.82)',
              backdropFilter: 'blur(34px) saturate(180%)',
              WebkitBackdropFilter: 'blur(34px) saturate(180%)',
              borderRadius: 20,
              border: '1px solid rgba(255,255,255,0.7)',
              boxShadow: '0 32px 90px rgba(0,0,0,0.32), inset 0 1px 0 rgba(255,255,255,0.9)',
              animation: 'eaiModalIn .22s cubic-bezier(.2,.8,.3,1)',
            }}
          >
            {/* macOS 标题栏：交通灯 + 标题 */}
            <div style={{ padding: '14px 18px', borderBottom: '1px solid rgba(0,0,0,0.06)', display: 'flex', alignItems: 'center', gap: 14, flexShrink: 0 }}>
              <div style={{ display: 'flex', gap: 7 }}>
                <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#ff5f57' }} />
                <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#febc2e' }} />
                <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#28c840' }} />
              </div>
              <span style={{ flex: 1, fontWeight: 600, fontSize: 13, letterSpacing: 0.3, color: '#1d1d1f' }}>
                编辑{detail ? TYPE_LABEL[detail.entity_type] || '' : ''}卡片 · Markdown
              </span>
              <span onClick={handleCloseEdit} style={{ cursor: 'pointer', color: '#6e6e73', fontSize: 15, lineHeight: 1, padding: '4px 8px', borderRadius: 6 }}>✕</span>
            </div>
            {/* 编辑器主体 */}
            <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: 14 }}>
              <div style={{ borderRadius: 12, overflow: 'hidden', border: '1px solid rgba(0,0,0,0.07)' }}>
                <div data-color-mode="light">
                  <MDEditor value={mdValue} onChange={(v) => { setMdValue(v || ''); setDirty(true) }} height={400} preview="live" />
                </div>
              </div>
            </div>
            {/* 底部操作 */}
            <div style={{ padding: '12px 18px', borderTop: '1px solid rgba(0,0,0,0.06)', display: 'flex', justifyContent: 'flex-end', gap: 8, flexShrink: 0 }}>
              <Button className="mac-btn" onClick={handleCloseEdit}>取消</Button>
              <Button className="mac-btn" type="primary" onClick={handleSaveMd}>保存</Button>
            </div>
          </div>
        </div>
      )}
    </Splitter>
  )
}
