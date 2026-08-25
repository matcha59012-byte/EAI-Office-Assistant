import axios from 'axios'

export interface MeetingSource {
  id: number
  title: string
  file_name: string
  source_type: string
  status: string
  created_at: string
}

export interface PendingItem {
  pending_id: number
  source_id: number
  entity_type: 'customer' | 'project' | 'company'
  card: Record<string, any>
  card_md: string
}

export interface EntityItem {
  id: number
  entity_type: 'customer' | 'project' | 'company'
  name: string
  card: Record<string, any>
  card_md: string
  source_meeting_id: number | null
  created_at: string
}

export interface ExtractResult {
  source_id: number
  cleaned: string
  items: { pending_id: number; entity_type: string; card: Record<string, any>; card_md: string; diff: string }[]
}

// 源文件
export function uploadMeetingSource(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  return axios.post<{ id: number; title: string; status: string }>('/api/meeting/sources', fd).then((r) => r.data)
}

export function transcribeAudio(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  return axios.post<{ id: number; title: string; status: string }>('/api/meeting/transcribe', fd).then((r) => r.data)
}

export function listMeetingSources() {
  return axios.get<MeetingSource[]>('/api/meeting/sources').then((r) => r.data)
}

export function getMeetingSource(id: number) {
  return axios.get<{ id: number; title: string; content: string; status: string; source_type: string }>(`/api/meeting/sources/${id}`).then((r) => r.data)
}

export function deleteMeetingSource(id: number) {
  return axios.delete(`/api/meeting/sources/${id}`).then((r) => r.data)
}

export function scanSources() {
  return axios.post<{ imported: number; sources: { source_id: number; file: string; title: string }[] }>('/api/meeting/scan').then((r) => r.data)
}

// 提取 / 确认
export function extractMeetingEntities(sourceId: number) {
  return axios.post<ExtractResult>('/api/meeting/extract', { source_id: sourceId }).then((r) => r.data)
}

export function confirmEntity(pendingId: number, card?: Record<string, any>) {
  return axios
    .post('/api/meeting/confirm', { pending_id: pendingId, card: card ?? null })
    .then((r) => r.data)
}

export function skipEntity(pendingId: number) {
  return axios.post('/api/meeting/skip', { pending_id: pendingId }).then((r) => r.data)
}

export function listPending() {
  return axios.get<PendingItem[]>('/api/meeting/pending').then((r) => r.data)
}

export function listEntities(entityType?: string) {
  return axios
    .get<EntityItem[]>('/api/meeting/entities', { params: entityType ? { entity_type: entityType } : {} })
    .then((r) => r.data)
}
