import React, { useEffect, useState } from 'react'
import { fetchStandings } from '../services/api'

export default function StandingsPage() {
  const [standings, setStandings] = useState([])
  const [loading, setLoading]     = useState(true)
  const [error, setError]         = useState('')

  useEffect(() => {
    fetchStandings()
      .then(d => setStandings(d.standings || []))
      .catch(e => setError(e.response?.data?.detail || 'Failed to load standings'))
      .finally(() => setLoading(false))
  }, [])

  const maxPts = standings[0]?.points || 1

  return (
    <div style={{ paddingTop:52, minHeight:'100vh' }}>
      <div style={{ maxWidth:900, margin:'0 auto', padding:'40px 24px' }}>

        <div className="fade-up" style={{ marginBottom:28 }}>
          <span className="section-label">// Live Standings · 2024/25 Season</span>
          <h1 style={{ fontSize:'2rem', fontWeight:800, color:'#ffffff', letterSpacing:'-0.02em' }}>
            La Liga Table
          </h1>
        </div>

        {error && (
          <div style={{ padding:'12px 16px', background:'rgba(248,113,113,0.05)', border:'1px solid rgba(248,113,113,0.15)', borderRadius:3, marginBottom:20, fontSize:'0.78rem', color:'#f87171', fontFamily:'monospace' }}>
            ✗ {error}
          </div>
        )}

        {loading && (
          <div style={{ color:'rgba(255,255,255,0.2)', fontFamily:'monospace', padding:'40px 0', fontSize:'0.82rem' }}>
            Loading standings…
          </div>
        )}

        {!loading && standings.length > 0 && (
          <div className="card fade-up" style={{ overflow:'hidden' }}>
            <table className="tbl">
              <thead>
                <tr>
                  {['#','Club','MP','W','D','L','GF','GA','GD','Pts'].map(h => <th key={h}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {standings.map((row, i) => (
                  <tr key={row.team}>
                    <td>
                      <span style={{
                        fontFamily:'monospace', fontWeight:700, fontSize:'0.82rem',
                        color: i < 4 ? 'var(--cyan)' : i >= standings.length-3 ? '#f87171' : 'rgba(255,255,255,0.3)',
                      }}>{row.position}</span>
                    </td>
                    <td>
                      <div style={{ display:'flex', alignItems:'center', gap:10 }}>
                        {row.crest && (
                          <img src={row.crest} alt="" style={{ width:20, height:20, objectFit:'contain', opacity:0.85 }}
                            onError={e => e.target.style.display='none'} />
                        )}
                        <span style={{ fontWeight:600, color:'#ffffff', fontSize:'0.86rem' }}>{row.team}</span>
                      </div>
                    </td>
                    <td style={{ color:'rgba(255,255,255,0.4)', fontFamily:'monospace', fontSize:'0.8rem' }}>{row.played}</td>
                    <td style={{ color:'var(--cyan)', fontFamily:'monospace', fontSize:'0.8rem' }}>{row.won}</td>
                    <td style={{ color:'rgba(255,255,255,0.35)', fontFamily:'monospace', fontSize:'0.8rem' }}>{row.draw}</td>
                    <td style={{ color:'#f87171', fontFamily:'monospace', fontSize:'0.8rem' }}>{row.lost}</td>
                    <td style={{ color:'rgba(255,255,255,0.4)', fontFamily:'monospace', fontSize:'0.8rem' }}>{row.goals_for}</td>
                    <td style={{ color:'rgba(255,255,255,0.4)', fontFamily:'monospace', fontSize:'0.8rem' }}>{row.goals_against}</td>
                    <td style={{ fontFamily:'monospace', fontSize:'0.8rem', color: row.goal_diff >= 0 ? 'var(--cyan)' : '#f87171' }}>
                      {row.goal_diff > 0 ? `+${row.goal_diff}` : row.goal_diff}
                    </td>
                    <td>
                      <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                        <span style={{ fontFamily:'monospace', fontWeight:800, color:'#ffffff', fontSize:'0.92rem', minWidth:24 }}>
                          {row.points}
                        </span>
                        <div style={{ width:36, height:2, background:'#111', borderRadius:1 }}>
                          <div style={{ height:'100%', background:'var(--cyan)', borderRadius:1, opacity:0.5, width:`${(row.points/maxPts)*100}%` }} />
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ padding:'10px 16px', borderTop:'1px solid #0f0f0f', display:'flex', gap:20, fontSize:'0.62rem', color:'rgba(255,255,255,0.2)', fontFamily:'monospace' }}>
              <span><span style={{ color:'var(--cyan)', opacity:0.6 }}>■</span> Champions League (Top 4)</span>
              <span><span style={{ color:'#f87171', opacity:0.6 }}>■</span> Relegation (Bottom 3)</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}