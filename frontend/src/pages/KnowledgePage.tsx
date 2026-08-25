import { useState } from 'react'
import { Splitter } from 'antd'
import LibraryPanel from '../components/LibraryPanel'
import DocViewer from '../components/DocViewer'
import ChatPanel from '../components/ChatPanel'

export default function KnowledgePage() {
  const [docId, setDocId] = useState<number | null>(null)
  const [currentLibrary, setCurrentLibrary] = useState<string>('企业管理')
  const [currentSessionId, setCurrentSessionId] = useState<number | null>(null)

  return (
    <Splitter style={{ height: '100%' }}>
      {/* 左栏：资料库（文档 + 会话，可折叠） */}
      <Splitter.Panel defaultSize="18%" min={56} max="32%" collapsible>
        <div className="glass" style={{ height: '100%', overflow: 'hidden' }}>
          <LibraryPanel
            currentDocId={docId}
            onSelectDoc={setDocId}
            currentLibrary={currentLibrary}
            onSelectLibrary={setCurrentLibrary}
            currentSessionId={currentSessionId}
            onSelectSession={setCurrentSessionId}
            onSessionChanged={(deletedId) => {
              if (deletedId != null && deletedId === currentSessionId) {
                setCurrentSessionId(null)
              }
            }}
          />
        </div>
      </Splitter.Panel>

      {/* 中栏：文档查看（md，主区） */}
      <Splitter.Panel>
        <div className="glass" style={{ height: '100%', overflow: 'hidden' }}>
          <DocViewer docId={docId} />
        </div>
      </Splitter.Panel>

      {/* 右栏：AI 问答（可收起） */}
      <Splitter.Panel defaultSize="30%" min={220} max="50%" collapsible>
        <div className="glass" style={{ height: '100%', overflow: 'hidden' }}>
          <ChatPanel
            sessionScope="kb"
            currentSessionId={currentSessionId}
            library={currentLibrary}
            onOpenDoc={setDocId}
          />
        </div>
      </Splitter.Panel>
    </Splitter>
  )
}
