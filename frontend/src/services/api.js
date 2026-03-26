import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8001',
  timeout: 30000,
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
export const fetchUpcomingPredictions = ()         => api.get('/predict/upcoming').then(r => r.data)
export const fetchModelInfo         = ()           => api.get('/model/info').then(r => r.data)

export default api