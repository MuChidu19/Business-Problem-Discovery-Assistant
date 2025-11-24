import axios from 'axios'

// Allow VITE_API_URL to be set as either http://host:port or http://host:port/api
const rawBase = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const baseURL = rawBase.replace(/\/+$/, '')

export const api = axios.create({ baseURL })

// If baseURL already ends with /api, avoid double /api in request paths
const normalize = (path) => (baseURL.endsWith('/api') ? path.replace(/^\/api/, '') : path)

export function setAuthToken(token) {
  if (token) api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  else delete api.defaults.headers.common['Authorization']
}

export const getConstants = async () => {
  const { data } = await api.get(normalize('/api/constants/accounts'))
  return data
}

export const analyze = async (agent, payload) => {
  const { data } = await api.post(normalize(`/api/agents/${agent}/analyze`), payload)
  return data
}

export const postFeedback = async (payload) => {
  const { data } = await api.post(normalize('/api/feedback'), payload)
  return data
}

export const getFeedback = async () => {
  const { data } = await api.get(normalize('/api/admin/feedback'))
  return data
}
