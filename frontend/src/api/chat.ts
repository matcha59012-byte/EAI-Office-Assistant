import axios from 'axios'

export interface SessionItem {
  id: number
  title: string
  created_at: string
}

export interface MessageItem {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface SourceItem {
  doc_id: number | null
  chunk_index: number | null
  text: string
  similarity: number
}

export interface AskResult {
  answer: string
  sources: SourceItem[]
  rejected: boolean
}

// ---------- 会话 ----------
export function listSessions(scope: string) {
  return axios.get<SessionItem[]>(`/api/${scope}/sessions`).then((r) => r.data)
}

export function createSession(scope: string, title?: string) {
  return axios
    .post<{ id: number; title: string }>(`/api/${scope}/sessions`, { title: title || '新会话' })
    .then((r) => r.data)
}

export function deleteSession(scope: string, id: number) {
  return axios.delete(`/api/${scope}/sessions/${id}`).then((r) => r.data)
}

export function renameSession(scope: string, id: number, title: string) {
  return axios.put(`/api/${scope}/sessions/${id}`, { title }).then((r) => r.data)
}

export function getMessages(scope: string, sessionId: number) {
  return axios.get<MessageItem[]>(`/api/${scope}/sessions/${sessionId}/messages`).then((r) => r.data)
}

export function sendMessage(scope: string, sessionId: number, question: string, docId?: number | null, library?: string | null) {
  return axios
    .post<AskResult>(`/api/${scope}/sessions/${sessionId}/messages`, {
      question,
      doc_id: docId ?? null,
      library: library ?? null,
    })
    .then((r) => r.data)
}

// ---------- 资料库（文件夹） ----------
export interface LibraryItem {
  name: string
  count: number
}

export function listLibraries() {
  return axios.get<LibraryItem[]>('/api/kb/libraries').then((r) => r.data)
}

// ---------- 文档 ----------
export interface DocItem {
  id: number
  title: string
  file_type: string
  library: string
  created_at: string
}

export function listDocuments(library?: string | null) {
  return axios
    .get<DocItem[]>('/api/kb/documents', { params: library ? { library } : {} })
    .then((r) => r.data)
}

export function getDocumentContent(id: number) {
  return axios.get<{ id: number; title: string; content: string }>(`/api/kb/documents/${id}/content`).then((r) => r.data)
}

export function uploadDocument(file: File, library?: string) {
  const fd = new FormData()
  fd.append('file', file)
  if (library) fd.append('library', library)
  return axios
    .post<{ id: number; title: string; chunks: number }>('/api/kb/upload', fd)
    .then((r) => r.data)
}

export function deleteDocument(id: number) {
  return axios.delete(`/api/kb/documents/${id}`).then((r) => r.data)
}
