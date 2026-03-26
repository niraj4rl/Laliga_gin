import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { fetchUpcomingPredictions } from '../services/api'

function FormDot({ char }) {
  const color = char === 'W' ? '#22d3ee' : char === 'L' ? '#f87171' : '#404040'
  return <span style={{ display:'inline-block', width:7, height:7, borderRadius:'50%', background:color, marginRight:3 }} title={char} />
}

function SquadSection({ injuries, suspensions, keyPlayers, side }) {
  const hasData = injuries.length > 0 || suspensions.length > 0 || keyPlayers.length > 0
  if (!hasData) return null

  return (
    <div style={{ flex:1 }}>
      <div style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.3)', letterSpacing:'0.1em', textTransform:'uppercase', fontFamily:'monospace', marginBottom:8 }}>
        {side} Squad
      </div>

      {injuries.length > 0 && (
        <div style={{ marginBottom:6 }}>
          <div style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.2)', marginBottom:4, fontFamily:'monospace' }}>INJURED</div>
          <div style={{ display:'flex', flexWrap:'wrap', gap:4 }}>
            {injuries.map((p, i) => (
              <span key={i} className="injury-badge injured">✕ {p.name}</span>
            ))}
          </div>
        </div>
      )}

      {suspensions.length > 0 && (
        <div style={{ marginBottom:6 }}>
          <div style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.2)', marginBottom:4, fontFamily:'monospace' }}>SUSPENDED</div>
          <div style={{ display:'flex', flexWrap:'wrap', gap:4 }}>
            {suspensions.map((p, i) => (
              <span key={i} className="injury-badge suspended">⊘ {p.name}</span>
            ))}
          </div>
        </div>
      )}

      {keyPlayers.length > 0 && (
        <div>
          <div style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.2)', marginBottom:4, fontFamily:'monospace' }}>KEY PLAYERS</div>
          <div style={{ display:'flex', flexWrap:'wrap', gap:4 }}>
            {keyPlayers.map((p, i) => (
              <span key={i} style={{ fontSize:'0.65rem', padding:'2px 8px', borderRadius:100, border:'1px solid rgba(34,211,238,0.15)', color:'rgba(34,211,238,0.7)', fontFamily:'monospace' }}>
                ★ {p.name}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function PredCard({ p, onClick, isSelected }) {
  const resultLabel = p.predicted_result === 'home_win' ? p.home_team
    : p.predicted_result === 'away_win' ? p.away_team : 'Draw'
  const resultColor = p.predicted_result === 'home_win' ? 'var(--cyan)'
    : p.predicted_result === 'away_win' ? 'var(--mag)' : 'var(--amb)'
  const date    = new Date(p.date)
  const dateStr = date.toLocaleDateString('en-GB', { weekday:'short', day:'2-digit', month:'short' })
  const timeStr = date.toLocaleTimeString('en-GB', { hour:'2-digit', minute:'2-digit' })
  const homeInjuries = (p.home_injuries||[]).length + (p.home_suspensions||[]).length
  const awayInjuries = (p.away_injuries||[]).length + (p.away_suspensions||[]).length

  return (
    <div onClick={onClick} style={{
      background:'var(--bg2)',
      border:`1px solid ${isSelected ? 'rgba(34,211,238,0.2)' : 'var(--border)'}`,
      borderRadius:4, padding:'18px', cursor:'pointer', transition:'border-color 0.2s',
    }}
    onMouseEnter={e => { if (!isSelected) e.currentTarget.style.borderColor = '#2a2a2a' }}
    onMouseLeave={e => { if (!isSelected) e.currentTarget.style.borderColor = 'var(--border)' }}>

      {/* Top row */}
      <div style={{ display:'flex', justifyContent:'space-between', marginBottom:14 }}>
        <span style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.35)', fontFamily:'monospace' }}>
          MD{p.matchday} · {dateStr} {timeStr}
        </span>
        <span style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.2)', fontFamily:'monospace' }}>
          {p.confidence}% conf
        </span>
      </div>

      {/* Teams */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr auto 1fr', gap:8, alignItems:'center', marginBottom:14 }}>
        <div>
          <div style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.3)', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:3 }}>
            Home #{p.home_position}
            {homeInjuries > 0 && <span style={{ color:'#f87171', marginLeft:6 }}>⚕{homeInjuries}</span>}
          </div>
          <div style={{ fontWeight:700, color:'#ffffff', fontSize:'0.9rem', lineHeight:1.2 }}>{p.home_team}</div>
          <div style={{ marginTop:5 }}>
            {(p.home_form||'').split('').map((c,i) => <FormDot key={i} char={c} />)}
          </div>
        </div>
        <div style={{ fontSize:'0.65rem', color:'rgba(255,255,255,0.1)', fontWeight:800, textAlign:'center' }}>VS</div>
        <div style={{ textAlign:'right' }}>
          <div style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.3)', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:3 }}>
            Away #{p.away_position}
            {awayInjuries > 0 && <span style={{ color:'#f87171', marginLeft:6 }}>⚕{awayInjuries}</span>}
          </div>
          <div style={{ fontWeight:700, color:'#ffffff', fontSize:'0.9rem', lineHeight:1.2 }}>{p.away_team}</div>
          <div style={{ marginTop:5, textAlign:'right' }}>
            {(p.away_form||'').split('').map((c,i) => <FormDot key={i} char={c} />)}
          </div>
        </div>
      </div>

      {/* Prediction pill */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', padding:'7px 12px', background:'#050505', border:'1px solid #111', borderRadius:3, marginBottom:12 }}>
        <span style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.25)', textTransform:'uppercase', letterSpacing:'0.08em' }}>Prediction</span>
        <span style={{ fontWeight:800, color:resultColor, fontSize:'0.82rem' }}>
          {resultLabel === 'Draw' ? 'DRAW' : resultLabel.toUpperCase()}
        </span>
      </div>

      {/* Prob bars */}
      <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
        {[
          { label:'Home', value:p.home_win_prob, color:'var(--cyan)' },
          { label:'Draw', value:p.draw_prob,     color:'rgba(255,255,255,0.2)' },
          { label:'Away', value:p.away_win_prob, color:'var(--mag)' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ display:'flex', alignItems:'center', gap:6 }}>
            <span style={{ fontSize:'0.58rem', color:'rgba(255,255,255,0.25)', minWidth:28, textAlign:'right', fontFamily:'monospace' }}>{label}</span>
            <div style={{ flex:1, height:2, background:'#111', borderRadius:1 }}>
              <div className="bar-anim" style={{ height:'100%', background:color, borderRadius:1, '--w':`${value}%`, opacity:0.8 }} />
            </div>
            <span style={{ fontSize:'0.6rem', fontFamily:'monospace', color, minWidth:26 }}>{value}%</span>
          </div>
        ))}
      </div>

      <div style={{ marginTop:10, textAlign:'center', fontSize:'0.58rem', color:isSelected?'var(--cyan)':'rgba(255,255,255,0.1)', letterSpacing:'0.08em', transition:'color 0.2s' }}>
        {isSelected ? '▲ COLLAPSE' : '▼ VIEW ANALYSIS'}
      </div>
    </div>
  )
}

function AnalysisPanel({ p }) {
  const dominant     = p.home_win_prob > p.away_win_prob ? p.home_team : p.away_team
  const dominantProb = Math.max(p.home_win_prob, p.away_win_prob)
  const isClose      = Math.abs(p.home_win_prob - p.away_win_prob) < 10
  const homeInjuries = (p.home_injuries||[]).length
  const awayInjuries = (p.away_injuries||[]).length

  const insights = []
  if (p.home_position < p.away_position)
    insights.push(`${p.home_team} are ranked ${p.away_position - p.home_position} places higher in the table.`)
  else if (p.away_position < p.home_position)
    insights.push(`${p.away_team} sit ${p.home_position - p.away_position} spots above their hosts.`)
  if (p.home_avg_goals > 1.8)
    insights.push(`${p.home_team} averaging ${p.home_avg_goals} goals per game — sharp attack.`)
  if (p.away_avg_goals > 1.8)
    insights.push(`${p.away_team} carry real threat away, scoring ${p.away_avg_goals} per match.`)
  if (homeInjuries > 2)
    insights.push(`${p.home_team} have ${homeInjuries} players unavailable — weakened squad.`)
  if (awayInjuries > 2)
    insights.push(`${p.away_team} travel with ${awayInjuries} absentees — fitness concerns.`)
  if (p.draw_prob > 35)
    insights.push(`Draw probability elevated at ${p.draw_prob}% — evenly matched sides.`)
  if (isClose)
    insights.push(`Only ${Math.abs(p.home_win_prob - p.away_win_prob)}% separates win probabilities — genuine toss-up.`)
  if (dominantProb > 55)
    insights.push(`${dominant} are clear favorites at ${dominantProb}%.`)
  if (insights.length === 0)
    insights.push(`Competitive fixture — both sides have similar form and standing.`)

  const hasSquadData =
    (p.home_injuries||[]).length > 0 || (p.away_injuries||[]).length > 0 ||
    (p.home_suspensions||[]).length > 0 || (p.away_suspensions||[]).length > 0 ||
    (p.home_key_players||[]).length > 0 || (p.away_key_players||[]).length > 0

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity:0, height:0 }}
        animate={{ opacity:1, height:'auto' }}
        exit={{ opacity:0, height:0 }}
        transition={{ duration:0.28 }}
        style={{ overflow:'hidden' }}>
        <div style={{
          background:'#030303',
          border:'1px solid rgba(34,211,238,0.12)',
          borderTop:'none',
          borderRadius:'0 0 4px 4px',
          padding:'20px',
          marginTop:-4,
        }}>

          {/* Stats grid */}
          <span className="section-label">// Match Statistics</span>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr 1fr', gap:8, marginBottom:20 }}>
            {[
              { label:'Position',  home:`#${p.home_position}`, away:`#${p.away_position}` },
              { label:'Avg Goals', home:p.home_avg_goals,      away:p.away_avg_goals      },
              { label:'Points',    home:p.home_points||'—',    away:p.away_points||'—'    },
              { label:'Win Prob',  home:`${p.home_win_prob}%`, away:`${p.away_win_prob}%` },
            ].map(({ label, home, away }) => (
              <div key={label} style={{ background:'var(--bg2)', borderRadius:3, padding:'10px 12px', border:'1px solid var(--border)' }}>
                <div style={{ fontSize:'0.58rem', color:'rgba(255,255,255,0.25)', textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:7, fontFamily:'monospace' }}>{label}</div>
                <div style={{ display:'flex', justifyContent:'space-between' }}>
                  <span style={{ fontFamily:'monospace', fontSize:'0.85rem', color:'var(--cyan)', fontWeight:700 }}>{home}</span>
                  <span style={{ fontFamily:'monospace', fontSize:'0.85rem', color:'var(--mag)',  fontWeight:700 }}>{away}</span>
                </div>
                <div style={{ display:'flex', justifyContent:'space-between', marginTop:3 }}>
                  <span style={{ fontSize:'0.55rem', color:'rgba(255,255,255,0.15)' }}>home</span>
                  <span style={{ fontSize:'0.55rem', color:'rgba(255,255,255,0.15)' }}>away</span>
                </div>
              </div>
            ))}
          </div>

          {/* Squad info */}
          {hasSquadData && (
            <div style={{ marginBottom:20 }}>
              <span className="section-label">// Squad Availability</span>
              <div style={{ display:'flex', gap:20 }}>
                <SquadSection
                  injuries={p.home_injuries||[]}
                  suspensions={p.home_suspensions||[]}
                  keyPlayers={p.home_key_players||[]}
                  side="Home"
                />
                <div style={{ width:1, background:'var(--border)', flexShrink:0 }} />
                <SquadSection
                  injuries={p.away_injuries||[]}
                  suspensions={p.away_suspensions||[]}
                  keyPlayers={p.away_key_players||[]}
                  side="Away"
                />
              </div>
            </div>
          )}

          {/* Key insights */}
          <span className="section-label">// Key Insights</span>
          <div style={{ display:'flex', flexDirection:'column', gap:7, marginBottom:16 }}>
            {insights.map((ins, i) => (
              <div key={i} style={{ display:'flex', gap:10, alignItems:'flex-start' }}>
                <span style={{ color:'var(--cyan)', fontFamily:'monospace', fontSize:'0.7rem', marginTop:1, opacity:0.4, flexShrink:0 }}>→</span>
                <span style={{ fontSize:'0.78rem', color:'rgba(255,255,255,0.6)', lineHeight:1.6 }}>{ins}</span>
              </div>
            ))}
          </div>

          {/* Verdict */}
          <div style={{ padding:'12px 14px', background:'var(--bg2)', borderRadius:3, border:'1px solid var(--border)' }}>
            <span className="section-label">// Model Verdict</span>
            <div style={{ fontSize:'0.78rem', color:'rgba(255,255,255,0.55)', lineHeight:1.6 }}>
              {p.predicted_result === 'draw'
                ? `Model expects a draw (${p.draw_prob}%) — neither side has a decisive edge.`
                : `${p.predicted_result === 'home_win' ? p.home_team : p.away_team} predicted to win — ${dominantProb}% probability, ${p.confidence}% confidence.`
              }
              {(homeInjuries > 0 || awayInjuries > 0) && (
                <span style={{ color:'rgba(248,113,113,0.7)', display:'block', marginTop:4, fontSize:'0.72rem' }}>
                  ⚕ Injury impact factored into strength scores.
                </span>
              )}
            </div>
          </div>

        </div>
      </motion.div>
    </AnimatePresence>
  )
}

export default function PredictionsPage() {
  const [predictions, setPredictions] = useState([])
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState('')
  const [generatedAt, setGeneratedAt] = useState('')
  const [selected, setSelected]       = useState(null)

  const load = async () => {
    setLoading(true); setError(''); setSelected(null)
    try {
      const data = await fetchUpcomingPredictions()
      setPredictions(data.predictions || [])
      setGeneratedAt(data.generated_at || '')
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load. Check FOOTBALL_API_KEY in backend/.env')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div style={{ paddingTop:52, minHeight:'100vh' }}>
      <div style={{ maxWidth:1100, margin:'0 auto', padding:'40px 24px' }}>

        <div className="fade-up" style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-end', marginBottom:24, flexWrap:'wrap', gap:12 }}>
          <div>
            <span className="section-label">// AI Predictions · La Liga 2024/25</span>
            <h1 style={{ fontSize:'2rem', fontWeight:800, color:'#ffffff', letterSpacing:'-0.02em' }}>
              Upcoming Predictions
            </h1>
            {generatedAt && (
              <div style={{ fontSize:'0.6rem', color:'rgba(255,255,255,0.2)', fontFamily:'monospace', marginTop:4 }}>
                Updated {new Date(generatedAt).toLocaleString('en-GB')}
              </div>
            )}
          </div>
          <button className="btn-ghost" onClick={load} disabled={loading} style={{ fontSize:'0.75rem', padding:'7px 16px' }}>
            {loading ? '…' : '↻ Refresh'}
          </button>
        </div>

        {!loading && predictions.length > 0 && (
          <div style={{ fontSize:'0.62rem', color:'rgba(255,255,255,0.15)', fontFamily:'monospace', marginBottom:16, letterSpacing:'0.06em' }}>
            ↓ Click any card to view analysis, injuries and squad info
          </div>
        )}

        {error && (
          <div style={{ padding:'14px 18px', background:'rgba(248,113,113,0.05)', border:'1px solid rgba(248,113,113,0.15)', borderRadius:3, marginBottom:20, fontFamily:'monospace', fontSize:'0.78rem', color:'#f87171' }}>
            ✗ {error}
          </div>
        )}

        {loading && (
          <div style={{ color:'rgba(255,255,255,0.2)', fontFamily:'monospace', padding:'60px 0', textAlign:'center', fontSize:'0.82rem' }}>
            <div>Fetching fixtures, standings and squad data…</div>
            <div style={{ marginTop:8, fontSize:'0.7rem', color:'rgba(255,255,255,0.1)' }}>
              This may take 30–60 seconds on first load (API rate limit)
            </div>
          </div>
        )}

        {!loading && predictions.length > 0 && (
          <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(320px,1fr))', gap:2 }}>
            {predictions.map((p, i) => (
              <div key={i}>
                <PredCard
                  p={p}
                  onClick={() => setSelected(selected === i ? null : i)}
                  isSelected={selected === i}
                />
                {selected === i && <AnalysisPanel p={p} />}
              </div>
            ))}
          </div>
        )}

        {!loading && predictions.length === 0 && !error && (
          <div style={{ color:'rgba(255,255,255,0.15)', fontFamily:'monospace', padding:'60px 0', textAlign:'center' }}>
            No upcoming fixtures found
          </div>
        )}
      </div>
    </div>
  )
}