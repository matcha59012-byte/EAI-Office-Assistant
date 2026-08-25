import { useState } from 'react'
import { Tabs } from 'antd'
import {
  BookOutlined,
  FileTextOutlined,
  DatabaseOutlined,
} from '@ant-design/icons'
import KnowledgePage from './pages/KnowledgePage'
import MeetingPage from './pages/MeetingPage'
import CustomerPage from './pages/CustomerPage'

type PageKey = 'kb' | 'meeting' | 'customer'

export default function App() {
  const [page, setPage] = useState<PageKey>('kb')

  return (
    <div style={{ height: '100dvh', display: 'flex', flexDirection: 'column', padding: 10, gap: 10, overflow: 'hidden' }}>
      {/* 顶栏（玻璃）：第1行品牌，第2行功能Tab */}
      <div className="glass" style={{ flexShrink: 0, padding: '10px 16px 0', borderRadius: 12 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, paddingBottom: 4 }}>
          <span style={{ fontSize: 16, fontWeight: 700, letterSpacing: 0.3 }}>
            E-AI Office Assistant
          </span>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>企业AI智能办公助手</span>
        </div>
        <Tabs
          className="header-tabs"
          size="small"
          activeKey={page}
          onChange={(k) => setPage(k as PageKey)}
          items={[
            { key: 'kb', label: (<><BookOutlined /> 知识库</>) },
            { key: 'meeting', label: (<><FileTextOutlined /> 信息提取</>) },
            { key: 'customer', label: (<><DatabaseOutlined /> 客户数据</>) },
          ]}
        />
      </div>

      {/* 主内容区 */}
      <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {page === 'kb' && <KnowledgePage />}
        {page === 'meeting' && <MeetingPage />}
        {page === 'customer' && <CustomerPage />}
      </div>
    </div>
  )
}
