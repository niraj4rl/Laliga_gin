import React from 'react'
import { Link, useLocation } from 'react-router-dom'

const LINKS = [
  { to: '/predictions', label: 'Predictions' },
  { to: '/standings',   label: 'Standings'   },
  { to: '/results',     label: 'Results'     },
]

export default function Navbar() {
  const { pathname } = useLocation()
  if (pathname === '/') return null

  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
      background: 'rgba(0,0,0,0.94)', backdropFilter: 'blur(12px)',
      borderBottom: '1px solid #111',
    }}>
      <div style={{
        maxWidth: 1200, margin: '0 auto', padding: '0 24px',
        height: 52, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <Link to="/" style={{ textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 9 }}>
          <div style={{
            width: 26, height: 26,
            border: '1px solid rgba(34,211,238,0.35)', borderRadius: 3,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(34,211,238,0.06)',
          }}>
            <span style={{ color: 'var(--cyan)', fontSize: 8, fontWeight: 900, fontFamily: 'monospace' }}>GIN</span>
          </div>
          <span style={{ color: '#ffffff', fontSize: '0.9rem', fontWeight: 700, letterSpacing: '0.04em' }}>
            LaLiga<span style={{ color: 'var(--cyan)' }}>GIN</span>
          </span>
        </Link>

        <div style={{ display: 'flex', gap: 2 }}>
          {LINKS.map(({ to, label }) => {
            const active = pathname === to
            return (
              <Link key={to} to={to} style={{
                textDecoration: 'none', padding: '5px 14px', borderRadius: 100,
                fontSize: '0.78rem',
                fontWeight: active ? 600 : 400,
                color: active ? 'var(--cyan)' : 'rgba(255,255,255,0.45)',
                background: active ? 'rgba(34,211,238,0.06)' : 'transparent',
                border: active ? '1px solid rgba(34,211,238,0.2)' : '1px solid transparent',
                transition: 'all 0.15s',
              }}>
                {label}
              </Link>
            )
          })}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div className="pulse" style={{ width: 5, height: 5, background: 'var(--cyan)', borderRadius: '50%', opacity: 0.7 }} />
          <span style={{ fontSize: '0.62rem', color: 'rgba(255,255,255,0.25)', fontFamily: 'monospace', letterSpacing: '0.1em' }}>LIVE</span>
        </div>
      </div>
    </nav>
  )
}