import { http } from './http'

/** 与后端约定：可按实际路径调整 */

export async function loginApi({ username, password, role }) {
  const { data } = await http.post('/auth/login', { username, password, role })
  return data
}

export async function registerApi({ username, password }) {
  const { data } = await http.post('/auth/register', { username, password })
  return data
}

export async function fetchChallengeApi() {
  const { data } = await http.get('/door/challenge')
  return data
}

/**
 * @param {{ userId: string|number, challengeId?: string, passphrase: string, file: Blob }} payload
 */
export async function verifyDoorApi(payload) {
  const form = new FormData()
  form.append('userId', String(payload.userId))
  if (payload.challengeId != null) form.append('challengeId', String(payload.challengeId))
  form.append('passphrase', payload.passphrase)
  form.append('audio', payload.file, 'answer.wav')
  const { data } = await http.post('/door/verify', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function submitVoiceprintApi({ userId, files }) {
  const form = new FormData()
  form.append('userId', String(userId))
  files.forEach((blob, i) => {
    form.append(`segment${i + 1}`, blob, `seg${i + 1}.wav`)
  })
  const { data } = await http.post('/voiceprint/submit', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function fetchVoiceprintPromptsApi() {
  const { data } = await http.get('/voiceprint/prompts')
  return data
}

export async function createVisitorAuthApi({ userId, type }) {
  const { data } = await http.post('/visitor/auth', { userId, type })
  return data
}

export async function listVisitorAuthApi({ userId, page = 1, pageSize = 20 }) {
  const { data } = await http.get('/visitor/list', { params: { userId, page, pageSize } })
  return data
}

export async function deleteVisitorAuthApi(id) {
  const { data } = await http.delete(`/visitor/${id}`)
  return data
}

export async function fetchUserLogsApi({ userId, page = 1, pageSize = 20 }) {
  const { data } = await http.get('/logs/user', { params: { userId, page, pageSize } })
  return data
}

export async function fetchAdminStatsApi() {
  const { data } = await http.get('/admin/stats')
  return data
}

export async function fetchAdminDoorLogsApi({ page = 1, pageSize = 20 }) {
  const { data } = await http.get('/admin/logs/door', { params: { page, pageSize } })
  return data
}

export async function fetchAlarmsApi({ page = 1, pageSize = 20 }) {
  const { data } = await http.get('/admin/alarms', { params: { page, pageSize } })
  return data
}

export async function resolveAlarmApi(id) {
  const { data } = await http.post(`/admin/alarms/${id}/resolve`)
  return data
}

export async function fetchResidentsApi({ page = 1, pageSize = 20 }) {
  const { data } = await http.get('/admin/residents', { params: { page, pageSize } })
  return data
}
