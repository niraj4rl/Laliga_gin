import React, { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { fetchUpcomingPredictions } from '../services/api'

function FormDot({ char }) {
  const color = char === 'W' ? '#ffffff' : char === 'L' ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.5)'
  return <span style={{ display:'inline-block', width:7, height:7, borderRadius:'50%', background:color, marginRight:3 }} title={char} />
}

function PredCard({ p, onClick, isSelected }) {
  const resultLabel = p.predicted_result==='home_win' ? p.home_team
    : p.predicted_result==='away_win' ? p.away_team : 'Draw'
  const date    = new Date(p.date)
  const dateStr = date.toLocaleDateString('en-GB',{weekday:'short',day:'2-digit',month:'short'})
  const timeStr = date.toLocaleTimeString('en-GB',{hour:'2-digit',minute:'2-digit'})
  const hInj    = (p.home_injuries||[]).length + (p.home_suspensions||[]).length
  const aInj    = (p.away_injuries||[]).length + (p.away_suspensions||[]).length

  return (
    <div onClick={onClick} style={{
      background:'linear-gradient(155deg, rgba(34,211,238,0.04), rgba(0,0,0,0) 45%), var(--bg2)',
      border:`1px solid ${isSelected?'rgba(34,211,238,0.35)':'var(--border)'}`,
      borderRadius:4, padding:'18px', cursor:'pointer', transition:'border-color 0.2s',
    }}
    onMouseEnter={e=>{if(!isSelected)e.currentTarget.style.borderColor='rgba(34,211,238,0.22)'}}
    onMouseLeave={e=>{if(!isSelected)e.currentTarget.style.borderColor='var(--border)'}}>

      <div style={{display:'flex',justifyContent:'space-between',marginBottom:14}}>
        <span style={{fontSize:'0.6rem',color:'rgba(255,255,255,0.3)',fontFamily:'monospace'}}>
          MD{p.matchday} · {dateStr} {timeStr}
        </span>
        <span style={{fontSize:'0.6rem',color:'rgba(255,255,255,0.2)',fontFamily:'monospace'}}>
          {p.confidence}% conf
        </span>
      </div>

      <div style={{display:'grid',gridTemplateColumns:'1fr auto 1fr',gap:8,alignItems:'center',marginBottom:14}}>
        <div>
          <div style={{fontSize:'0.6rem',color:'rgba(255,255,255,0.3)',textTransform:'uppercase',letterSpacing:'0.06em',marginBottom:3}}>
            Home #{p.home_position}
            {hInj>0&&<span style={{color:'rgba(255,80,80,0.7)',marginLeft:6}}>⚕{hInj}</span>}
          </div>
          <div style={{display:'flex',alignItems:'center',gap:8}}>
            {p.home_crest && (
              <img
                src={p.home_crest}
                alt={`${p.home_team} crest`}
                style={{width:20,height:20,objectFit:'contain',opacity:0.9,filter:'drop-shadow(0 0 5px rgba(34,211,238,0.25))'}}
                onError={e => { e.currentTarget.style.display = 'none' }}
              />
            )}
            <div style={{fontWeight:700,color:'#ffffff',fontSize:'0.9rem',lineHeight:1.2}}>{p.home_team}</div>
          </div>
          <div style={{marginTop:5}}>
            {(p.home_form||'').split('').map((c,i)=><FormDot key={i} char={c}/>)}
          </div>
        </div>
        <div style={{fontSize:'0.65rem',color:'rgba(255,255,255,0.1)',fontWeight:800,textAlign:'center'}}>VS</div>
        <div style={{textAlign:'right'}}>
          <div style={{fontSize:'0.6rem',color:'rgba(255,255,255,0.3)',textTransform:'uppercase',letterSpacing:'0.06em',marginBottom:3}}>
            Away #{p.away_position}
            {aInj>0&&<span style={{color:'rgba(255,80,80,0.7)',marginLeft:6}}>⚕{aInj}</span>}
          </div>
          <div style={{display:'flex',alignItems:'center',justifyContent:'flex-end',gap:8}}>
            <div style={{fontWeight:700,color:'#ffffff',fontSize:'0.9rem',lineHeight:1.2}}>{p.away_team}</div>
            {p.away_crest && (
              <img
                src={p.away_crest}
                alt={`${p.away_team} crest`}
                style={{width:20,height:20,objectFit:'contain',opacity:0.9,filter:'drop-shadow(0 0 5px rgba(232,121,249,0.2))'}}
                onError={e => { e.currentTarget.style.display = 'none' }}
              />
            )}
          </div>
          <div style={{marginTop:5,textAlign:'right'}}>
            {(p.away_form||'').split('').map((c,i)=><FormDot key={i} char={c}/>)}
          </div>
        </div>
      </div>

      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',padding:'7px 12px',background:'#050505',border:'1px solid #111',borderRadius:3,marginBottom:12}}>
        <span style={{fontSize:'0.6rem',color:'rgba(255,255,255,0.25)',textTransform:'uppercase',letterSpacing:'0.08em'}}>Prediction</span>
        <span style={{fontWeight:800,color:'#ffffff',fontSize:'0.82rem'}}>
          {resultLabel==='Draw'?'DRAW':resultLabel.toUpperCase()}
        </span>
      </div>

      <div style={{display:'flex',flexDirection:'column',gap:6}}>
        {[
          {label:'Home',value:p.home_win_prob,color:'var(--cyan)'},
          {label:'Draw',value:p.draw_prob,color:'var(--amb)'},
          {label:'Away',value:p.away_win_prob,color:'var(--mag)'},
        ].map(({label,value})=>(
          <div key={label} style={{display:'flex',alignItems:'center',gap:6}}>
            <span style={{fontSize:'0.58rem',color:'rgba(255,255,255,0.25)',minWidth:28,textAlign:'right',fontFamily:'monospace'}}>{label}</span>
            <div style={{flex:1,height:2,background:'#111',borderRadius:1}}>
              <div className="bar-anim" style={{height:'100%',background:label==='Home'?'var(--cyan)':label==='Away'?'var(--mag)':'var(--amb)',borderRadius:1,opacity:0.75,'--w':`${value}%`}}/>
            </div>
            <span style={{fontSize:'0.6rem',fontFamily:'monospace',color:'rgba(255,255,255,0.7)',minWidth:26}}>{value}%</span>
          </div>
        ))}
      </div>

      <div style={{marginTop:10,textAlign:'center',fontSize:'0.58rem',color:isSelected?'rgba(255,255,255,0.5)':'rgba(255,255,255,0.1)',letterSpacing:'0.08em',transition:'color 0.2s'}}>
        {isSelected?'▲ COLLAPSE':'▼ VIEW ANALYSIS'}
      </div>
    </div>
  )
}

function AnalysisPanel({ p }) {
  const dominant     = p.home_win_prob>p.away_win_prob?p.home_team:p.away_team
  const dominantProb = Math.max(p.home_win_prob,p.away_win_prob)
  const isClose      = Math.abs(p.home_win_prob-p.away_win_prob)<10
  const hInj         = (p.home_injuries||[]).length
  const aInj         = (p.away_injuries||[]).length
  const hPenalty     = p.home_injury_penalty || 0
  const aPenalty     = p.away_injury_penalty || 0

  const insights = []
  if (p.home_position < p.away_position)
    insights.push(`${p.home_team} are ranked ${p.away_position-p.home_position} places higher in the table.`)
  else if (p.away_position < p.home_position)
    insights.push(`${p.away_team} sit ${p.home_position-p.away_position} spots above their hosts.`)
  if (p.home_avg_goals > 1.8)
    insights.push(`${p.home_team} averaging ${p.home_avg_goals} goals per game.`)
  if (p.away_avg_goals > 1.8)
    insights.push(`${p.away_team} scoring ${p.away_avg_goals} goals per match away.`)
  if (hInj > 1)
    insights.push(`${p.home_team} missing ${hInj} players — strength reduced by ${Math.round(hPenalty*100)}%.`)
  if (aInj > 1)
    insights.push(`${p.away_team} have ${aInj} absentees — strength reduced by ${Math.round(aPenalty*100)}%.`)

  // Highlight HIGH impact injuries
  const highImpactHome = [...(p.home_injuries||[]),...(p.home_suspensions||[])].filter(x=>x.impact_label==='HIGH')
  const highImpactAway = [...(p.away_injuries||[]),...(p.away_suspensions||[])].filter(x=>x.impact_label==='HIGH')
  if (highImpactHome.length > 0)
    insights.push(`KEY ABSENCE: ${highImpactHome.map(x=>x.name).join(', ')} out for ${p.home_team} — major impact on prediction.`)
  if (highImpactAway.length > 0)
    insights.push(`KEY ABSENCE: ${highImpactAway.map(x=>x.name).join(', ')} out for ${p.away_team} — major impact on prediction.`)

  if (p.draw_prob > 35)
    insights.push(`Draw probability elevated at ${p.draw_prob}% — evenly matched sides.`)
  if (isClose)
    insights.push(`Only ${Math.abs(p.home_win_prob-p.away_win_prob)}% separates win probabilities.`)
  if (dominantProb > 55)
    insights.push(`${dominant} are clear favorites at ${dominantProb}%.`)
  if (insights.length === 0)
    insights.push('Competitive fixture — both sides have similar form and standing.')

  return (
    <AnimatePresence>
      <motion.div
        initial={{opacity:0,height:0}} animate={{opacity:1,height:'auto'}}
        exit={{opacity:0,height:0}} transition={{duration:0.28}}
        style={{overflow:'hidden'}}>
        <div style={{
          background:'#030303',
          border:'1px solid rgba(255,255,255,0.08)',
          borderTop:'none',borderRadius:'0 0 4px 4px',
          padding:'20px',marginTop:-4,
        }}>

          {/* Stats grid */}
          <span className="section-label">// Match Statistics</span>
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr 1fr',gap:8,marginBottom:20}}>
            {[
              {label:'Position', home:`#${p.home_position}`, away:`#${p.away_position}`},
              {label:'Avg Goals',home:p.home_avg_goals,      away:p.away_avg_goals},
              {label:'Points',   home:p.home_points||'—',    away:p.away_points||'—'},
              {label:'Win Prob', home:`${p.home_win_prob}%`, away:`${p.away_win_prob}%`},
            ].map(({label,home,away})=>(
              <div key={label} style={{background:'linear-gradient(180deg, rgba(34,211,238,0.03), rgba(0,0,0,0)), var(--bg2)',borderRadius:3,padding:'10px 12px',border:'1px solid var(--border)'}}>
                <div style={{fontSize:'0.58rem',color:'rgba(255,255,255,0.25)',textTransform:'uppercase',letterSpacing:'0.06em',marginBottom:7,fontFamily:'monospace'}}>{label}</div>
                <div style={{display:'flex',justifyContent:'space-between'}}>
                  <span style={{fontFamily:'monospace',fontSize:'0.85rem',color:'var(--cyan)',fontWeight:700}}>{home}</span>
                  <span style={{fontFamily:'monospace',fontSize:'0.85rem',color:'var(--mag)',fontWeight:700}}>{away}</span>
                </div>
                <div style={{display:'flex',justifyContent:'space-between',marginTop:3}}>
                  <span style={{fontSize:'0.55rem',color:'rgba(255,255,255,0.15)'}}>home</span>
                  <span style={{fontSize:'0.55rem',color:'rgba(255,255,255,0.15)'}}>away</span>
                </div>
              </div>
            ))}
          </div>

          {/* Insights */}
          <span className="section-label">// Key Insights</span>
          <div style={{display:'flex',flexDirection:'column',gap:7,marginBottom:16}}>
            {insights.map((ins,i)=>(
              <div key={i} style={{display:'flex',gap:10,alignItems:'flex-start'}}>
                <span style={{color:'rgba(255,255,255,0.3)',fontFamily:'monospace',fontSize:'0.7rem',marginTop:1,flexShrink:0}}>→</span>
                <span style={{fontSize:'0.78rem',color:'rgba(255,255,255,0.6)',lineHeight:1.6}}>{ins}</span>
              </div>
            ))}
          </div>

          {/* Verdict */}
          <div style={{padding:'12px 14px',background:'var(--bg2)',borderRadius:3,border:'1px solid var(--border)'}}>
            <span className="section-label">// Model Verdict</span>
            <div style={{fontSize:'0.78rem',color:'rgba(255,255,255,0.55)',lineHeight:1.6}}>
              {p.predicted_result==='draw'
                ?`Model expects a draw (${p.draw_prob}%) — neither side has a decisive edge.`
                :`${p.predicted_result==='home_win'?p.home_team:p.away_team} predicted to win — ${dominantProb}% probability, ${p.confidence}% confidence.`
              }
              {(hPenalty>0||aPenalty>0)&&(
                <span style={{color:'rgba(255,120,120,0.6)',display:'block',marginTop:4,fontSize:'0.72rem'}}>
                  ⚕ Injury impact applied: {p.home_team} -{Math.round(hPenalty*100)}% · {p.away_team} -{Math.round(aPenalty*100)}%
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
  const [predictions,setPredictions] = useState([])
  const [loading,setLoading]         = useState(true)
  const [error,setError]             = useState('')
  const [generatedAt,setGeneratedAt] = useState('')
  const [selected,setSelected]       = useState(null)
  const [injuryMode,setInjuryMode]   = useState(true)

  const load = async () => {
    setLoading(true); setError(''); setSelected(null)
    try {
      const data = await fetchUpcomingPredictions()
      setPredictions(data.predictions||[])
      setGeneratedAt(data.generated_at||'')
      setInjuryMode(Boolean(data.include_injuries))
    } catch(e) {
      setError(e.response?.data?.detail||'Failed to load. Check FOOTBALL_API_KEY in backend/.env')
    } finally {
      setLoading(false)
    }
  }

  useEffect(()=>{load()},[])

  return (
    <div style={{paddingTop:52,minHeight:'100vh'}}>
      <div style={{maxWidth:1100,margin:'0 auto',padding:'40px 24px'}}>

        <div className="fade-up" style={{display:'flex',justifyContent:'space-between',alignItems:'flex-end',marginBottom:24,flexWrap:'wrap',gap:12}}>
          <div>
            <span className="section-label">// AI Predictions · La Liga</span>
            <h1 style={{fontSize:'2rem',fontWeight:800,color:'#ffffff',letterSpacing:'-0.02em'}}>
              Upcoming Predictions
            </h1>
            {generatedAt&&(
              <div style={{fontSize:'0.6rem',color:'rgba(255,255,255,0.2)',fontFamily:'monospace',marginTop:4}}>
                Updated {new Date(generatedAt).toLocaleString('en-GB')}
              </div>
            )}
          </div>
          <button className="btn-ghost" onClick={load} disabled={loading} style={{fontSize:'0.75rem',padding:'7px 16px'}}>
            {loading?'…':'↻ Refresh'}
          </button>
        </div>

        {!loading&&predictions.length>0&&(
          <div style={{fontSize:'0.62rem',color:'rgba(255,255,255,0.15)',fontFamily:'monospace',marginBottom:16,letterSpacing:'0.06em'}}>
            ↓ Click any card to view analysis
          </div>
        )}

        {!loading&&!error&&predictions.length>0&&!injuryMode&&(
          <div style={{padding:'10px 12px',background:'rgba(255,200,80,0.05)',border:'1px solid rgba(255,200,80,0.15)',borderRadius:3,marginBottom:14,fontFamily:'monospace',fontSize:'0.72rem',color:'rgba(255,220,140,0.8)'}}>
            Injury lookup is temporarily unavailable, so predictions are shown in fast mode.
          </div>
        )}

        {error&&(
          <div style={{padding:'14px 18px',background:'rgba(255,68,68,0.05)',border:'1px solid rgba(255,68,68,0.15)',borderRadius:3,marginBottom:20,fontFamily:'monospace',fontSize:'0.78rem',color:'rgba(255,100,100,0.8)'}}>
            ✗ {error}
          </div>
        )}

        {loading&&(
          <div style={{color:'rgba(255,255,255,0.2)',fontFamily:'monospace',padding:'60px 0',textAlign:'center',fontSize:'0.82rem'}}>
            <div>Fetching fixtures, standings and squad data…</div>
            <div style={{marginTop:8,fontSize:'0.7rem',color:'rgba(255,255,255,0.1)'}}>
              This may take 30–60 seconds on first load
            </div>
          </div>
        )}

        {!loading&&predictions.length>0&&(
          <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(320px,1fr))',gap:2}}>
            {predictions.map((p,i)=>(
              <div key={i}>
                <PredCard p={p} onClick={()=>setSelected(selected===i?null:i)} isSelected={selected===i}/>
                {selected===i&&<AnalysisPanel p={p}/>}
              </div>
            ))}
          </div>
        )}

        {!loading&&predictions.length===0&&!error&&(
          <div style={{color:'rgba(255,255,255,0.15)',fontFamily:'monospace',padding:'60px 0',textAlign:'center'}}>
            No upcoming fixtures found
          </div>
        )}
      </div>
    </div>
  )
}