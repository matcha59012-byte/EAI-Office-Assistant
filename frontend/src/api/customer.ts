import axios from 'axios'

export interface CustomerEntity {
  id: number
  entity_type: 'customer' | 'project' | 'company'
  name: string
  card: Record<string, any>
  card_md: string
  status: string
  last_contact: string
  source_meeting_id: number | null
  created_at: string
}

export interface AlertItem {
  id: number
  name: string
  company: string
  status: string
  last_contact: string
  days: number | null
}

export interface Dashboard {
  customers: number
  projects: number
  companies: number
  total: number
  status_dist: Record<string, number>
  silent: number
}

export function listCustomerEntities(entityType: string, status?: string, q?: string) {
  return axios
    .get<CustomerEntity[]>('/api/customer/entities', {
      params: { entity_type: entityType, status: status || undefined, q: q || undefined },
    })
    .then((r) => r.data)
}

export function getCustomerEntity(id: number) {
  return axios.get<CustomerEntity>(`/api/customer/entities/${id}`).then((r) => r.data)
}

export function updateCustomerEntity(id: number, data: { name?: string; card?: Record<string, any>; card_md?: string; status?: string; last_contact?: string }) {
  return axios.put<CustomerEntity>(`/api/customer/entities/${id}`, data).then((r) => r.data)
}

export function followCustomerEntity(id: number, status?: string) {
  return axios.post<CustomerEntity>(`/api/customer/entities/${id}/follow`, { status: status || '跟进中' }).then((r) => r.data)
}

export function deleteCustomerEntity(id: number) {
  return axios.delete(`/api/customer/entities/${id}`).then((r) => r.data)
}

export function importCustomers(file: File) {
  const fd = new FormData()
  fd.append('file', file)
  return axios.post<{ imported: number; skipped: number }>('/api/customer/import', fd).then((r) => r.data)
}

export function customerAlerts() {
  return axios.get<AlertItem[]>('/api/customer/alerts').then((r) => r.data)
}

export function customerDashboard() {
  return axios.get<Dashboard>('/api/customer/dashboard').then((r) => r.data)
}

export function askEntity(question: string) {
  return axios
    .post<{ answer: string; sources: { id: number; type: string; name: string }[] }>('/api/customer/ask', { question })
    .then((r) => r.data)
}
