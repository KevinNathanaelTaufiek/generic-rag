import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
})

api.interceptors.request.use((config) => {
  const username = localStorage.getItem('rag_username') ?? 'anonymous'
  config.headers['X-Username'] = username
  return config
})

export default api
