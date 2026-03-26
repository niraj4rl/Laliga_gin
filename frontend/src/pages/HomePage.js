import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ShaderAnimation } from '../components/ShaderAnimation.js'

const WORDS = ['PREDICT', 'ANALYZE', 'DOMINATE']

function Typewriter() {
  const [wordIndex, setWordIndex] = useState(0)
  const [displayed, setDisplayed] = useState('')
  const [typing, setTyping]       = useState(true)

  useEffect(() => {
    const word = WORDS[wordIndex]
    let t
    if (typing) {
      if (displayed.length < word.length)
        t = setTimeout(() => setDisplayed(word.slice(0, displayed.length + 1)), 90)
      else
        t = setTimeout(() => setTyping(false), 2200)
    } else {
      if (displayed.length > 0)
        t = setTimeout(() => setDisplayed(displayed.slice(0, -1)), 45)
      else { setWordIndex(i => (i + 1) % WORDS.length); setTyping(true) }
    }
    return () => clearTimeout(t)
  }, [displayed, typing, wordIndex])

  return (
    <span style={{ color: '#ffffff' }}>
      {displayed}
      <span className="blink" style={{ color: '#ffffff' }}>|</span>
    </span>
  )
}

export default function HomePage() {
  return (
    <div style={{ minHeight: '100vh', position: 'relative', background: '#000', overflow: 'hidden' }}>
      <ShaderAnimation />
      <div style={{
        position: 'absolute', inset: 0, zIndex: 1, pointerEvents: 'none',
        background: 'linear-gradient(to bottom, rgba(0,0,0,0.5) 0%, rgba(0,0,0,0.72) 60%, rgba(0,0,0,0.92) 100%)',
      }} />

      {/* Nav */}
      <nav style={{
        position: 'relative', zIndex: 10,
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '22px 48px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 30, height: 30,
            border: '1px solid rgba(255,255,255,0.3)',
            borderRadius: 4,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(255,255,255,0.05)',
          }}>
            <span style={{ color: '#ffffff', fontSize: 9, fontWeight: 900, fontFamily: 'monospace' }}>GIN</span>
          </div>
          <span style={{ color: '#ffffff', fontSize: '1rem', fontWeight: 700, letterSpacing: '0.05em' }}>
            LaLigaGIN
          </span>
        </div>

        <div style={{ display: 'flex', gap: 4 }}>
          {[
            { to: '/predictions', label: 'Predictions' },
            { to: '/standings',   label: 'Standings'   },
            { to: '/results',     label: 'Results'     },
          ].map(({ to, label }) => (
            <Link key={to} to={to} style={{
              textDecoration: 'none', padding: '6px 16px',
              fontSize: '0.78rem', color: '#ffffff',
              borderRadius: 100, border: '1px solid transparent',
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.target.style.borderColor = 'rgba(255,255,255,0.3)' }}
            onMouseLeave={e => { e.target.style.borderColor = 'transparent' }}>
              {label}
            </Link>
          ))}
        </div>
      </nav>

      {/* Hero */}
      <div style={{
        position: 'relative', zIndex: 10,
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        minHeight: 'calc(100vh - 80px)',
        textAlign: 'center', padding: '0 24px',
      }}>

        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.7 }}
          style={{ marginBottom: 32 }}
        >
          <span style={{
            fontSize: '0.65rem', fontFamily: 'monospace',
            padding: '3px 14px',
            border: '1px solid rgba(255,255,255,0.2)',
            color: '#ffffff',
            borderRadius: 100, letterSpacing: '0.08em',
          }}>
            GAME INTELLIGENCE NETWORK
          </span>
        </motion.div>

        {/* Heading */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6, duration: 0.9 }}
          style={{
            fontSize: 'clamp(3.5rem, 11vw, 10rem)',
            fontWeight: 900,
            lineHeight: 0.88,
            letterSpacing: '-0.04em',
            marginBottom: 52,
            color: '#ffffff',
          }}
        >
          <Typewriter /><br />
          <span style={{
            color: 'transparent',
            WebkitTextStroke: '1px rgba(255,255,255,0.25)',
          }}>
            THE ODDS
          </span>
        </motion.h1>

        {/* CTAs */}
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.0, duration: 0.6 }}
          style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}
        >
          <Link to="/predictions" style={{ textDecoration: 'none' }}>
            <button style={{
              background: '#ffffff', color: '#000000',
              fontWeight: 700, fontSize: '0.82rem',
              letterSpacing: '0.08em', padding: '11px 32px',
              border: 'none', borderRadius: 100,
              cursor: 'pointer', transition: 'all 0.2s',
              textTransform: 'uppercase',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = '#e5e5e5'; e.currentTarget.style.transform = 'translateY(-1px)' }}
            onMouseLeave={e => { e.currentTarget.style.background = '#ffffff'; e.currentTarget.style.transform = 'translateY(0)' }}>
              View Predictions →
            </button>
          </Link>
          <Link to="/standings" style={{ textDecoration: 'none' }}>
            <button style={{
              background: 'transparent', color: '#ffffff',
              fontWeight: 500, fontSize: '0.82rem',
              padding: '10px 28px',
              border: '1px solid rgba(255,255,255,0.3)',
              borderRadius: 100, cursor: 'pointer', transition: 'all 0.2s',
            }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = '#ffffff'; e.currentTarget.style.background = 'rgba(255,255,255,0.05)' }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.3)'; e.currentTarget.style.background = 'transparent' }}>
              Live Standings
            </button>
          </Link>
        </motion.div>

        {/* Stats */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.4, duration: 1.0 }}
          style={{
            display: 'flex', gap: 56, marginTop: 96,
            borderTop: '1px solid rgba(255,255,255,0.08)',
            paddingTop: 36,
            flexWrap: 'wrap', justifyContent: 'center',
          }}
        >
          {[
            { value: '3,800+', label: 'Matches'  },
            { value: '10',     label: 'Seasons'  },
            { value: '55%+',   label: 'Accuracy' },
            { value: 'Live',   label: 'Real-Time' },
          ].map(({ value, label }) => (
            <div key={label} style={{ textAlign: 'center' }}>
              <div style={{
                fontSize: 'clamp(1.4rem, 3vw, 2rem)',
                fontWeight: 800, color: '#ffffff',
                fontFamily: 'monospace',
              }}>{value}</div>
              <div style={{
                fontSize: '0.62rem',
                color: 'rgba(255,255,255,0.4)',
                letterSpacing: '0.14em',
                textTransform: 'uppercase',
                marginTop: 4,
              }}>{label}</div>
            </div>
          ))}
        </motion.div>
      </div>

      {/* Footer */}
      <div style={{ position: 'relative', zIndex: 10, textAlign: 'center', paddingBottom: 24 }}>
        <span style={{
          fontSize: '0.58rem',
          color: 'rgba(255,255,255,0.12)',
          letterSpacing: '0.15em',
          fontFamily: 'monospace',
        }}>
          LALIGA GIN © 2025 · PREDICT · ANALYZE · WIN
        </span>
      </div>
    </div>
  )
}