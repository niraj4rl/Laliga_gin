import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 90000,
})

// Auto retry on 429 rate limit
api.interceptors.response.use(
  res => res,
  async err => {
    const config = err.config
    if (err.response?.status === 429 && !config._retry) {
      config._retry = true
      const wait = parseInt(err.response.data?.message?.match(/\d+/)?.[0] || '60') * 1000
      await new Promise(r => setTimeout(r, wait + 2000))
      return api(config)
    }
    return Promise.reject(err)
  }
)

export const fetchTeams             = ()           => api.get('/teams').then(r => r.data.teams)
export const fetchTeam              = (name)       => api.get(`/team/${encodeURIComponent(name)}`).then(r => r.data)
export const fetchStandings         = ()           => api.get('/live/standings').then(r => r.data)
export const fetchResults           = ()           => api.get('/live/results').then(r => r.data)
export const fetchUpcomingPredictions = async ()   => {
  try {
    const res = await api.get('/predict/upcoming', { params: { include_injuries: true } })
    return { ...res.data, include_injuries: true }
  } catch (err) {
    const status = err.response?.status
    const shouldFallback = err.code === 'ECONNABORTED' || status === 429 || (status >= 500) || !err.response
    if (!shouldFallback) throw err

    const res = await api.get('/predict/upcoming', { params: { include_injuries: false } })
    return { ...res.data, include_injuries: false }
  }
}
export const fetchModelInfo         = ()           => api.get('/model/info').then(r => r.data)

export default api