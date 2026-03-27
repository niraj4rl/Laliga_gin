import React, { useEffect, useState } from 'react'
import { fetchResults } from '../services/api'

export default function ResultsPage() {
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')

  useEffect(() => {
    fetchResults()
      .then(d => setResults(d.results || []))
      .catch(e => setError(e.response?.data?.detail || 'Failed to load results'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div style={{ paddingTop:52, minHeight:'100vh' }}>
      <div style={{ maxWidth:800, margin:'0 auto', padding:'40px 24px' }}>

        <div className="fade-up" style={{ marginBottom:28 }}>
          <span className="section-label">// Recent Results · 2025/26 Season</span>
          <h1 style={{ fontSize:'2rem', fontWeight:800, color:'#ffffff', letterSpacing:'-0.02em' }}>
            Latest Results
          </h1>
        </div>

        {error && (
          <div style={{ padding:'12px 16px', background:'rgba(248,113,113,0.05)', border:'1px solid rgba(248,113,113,0.15)', borderRadius:3, marginBottom:20, fontSize:'0.78rem', color:'#f87171', fontFamily:'monospace' }}>
            ✗ {error}
          </div>
        )}

        {loading && (
          <div style={{ color:'rgba(255,255,255,0.2)', fontFamily:'monospace', padding:'40px 0', fontSize:'0.82rem' }}>
            Loading results…
          </div>
        )}

        {!loading && results.length > 0 && (
          <div className="fade-up" style={{ display:'flex', flexDirection:'column', gap:2 }}>
            {results.map((r, i) => {
              const date    = new Date(r.date)
              const dateStr = date.toLocaleDateString('en-GB', { weekday:'short', day:'2-digit', month:'short' })
              const homeWon = r.result === 'home'
              const awayWon = r.result === 'away'
              return (
                <div key={i} className="card" style={{ padding:'14px 20px' }}>
                  <div style={{ display:'grid', gridTemplateColumns:'1fr auto 1fr', alignItems:'center', gap:16 }}>
                    <div style={{ display:'flex', alignItems:'center', justifyContent:'flex-end', gap:8 }}>
                      {r.home_crest && <img src={r.home_crest} alt="" style={{ width:22, height:22, objectFit:'contain', opacity:0.85 }} onError={e => e.target.style.display='none'} />}
                      <span style={{ fontWeight:homeWon?700:400, color:homeWon?'#ffffff':'rgba(255,255,255,0.35)', fontSize:'0.86rem' }}>
                        {r.home_team}
                      </span>
                    </div>
                    <div style={{ textAlign:'center', minWidth:80 }}>
                      <div style={{ fontFamily:'monospace', fontWeight:900, fontSize:'1.3rem', letterSpacing:'0.04em' }}>
                        <span style={{ color:homeWon?'var(--cyan)':'rgba(255,255,255,0.6)' }}>{r.home_score}</span>
                        <span style={{ color:'rgba(255,255,255,0.1)', margin:'0 4px' }}>—</span>
                        <span style={{ color:awayWon?'var(--mag)':'rgba(255,255,255,0.6)' }}>{r.away_score}</span>
                      </div>
                      <div style={{ fontSize:'0.58rem', color:'rgba(255,255,255,0.2)', fontFamily:'monospace', marginTop:2 }}>
                        {dateStr} · MD{r.matchday}
                      </div>
                    </div>
                    <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                      {r.away_crest && <img src={r.away_crest} alt="" style={{ width:22, height:22, objectFit:'contain', opacity:0.85 }} onError={e => e.target.style.display='none'} />}
                      <span style={{ fontWeight:awayWon?700:400, color:awayWon?'#ffffff':'rgba(255,255,255,0.35)', fontSize:'0.86rem' }}>
                        {r.away_team}
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {!loading && results.length === 0 && !error && (
          <div style={{ color:'rgba(255,255,255,0.15)', fontFamily:'monospace', padding:'40px 0' }}>No results found</div>
        )}
      </div>
    </div>
  )
}