import React from 'react'
import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar.js'
import HomePage from './pages/HomePage.js'
import PredictionsPage from './pages/PredictionsPage.js'
import StandingsPage from './pages/StandingsPage.js'
import ResultsPage from './pages/ResultsPage.js'

export default function App() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)' }}>
      <Navbar />
      <Routes>
        <Route path="/"           element={<HomePage />} />
        <Route path="/predictions" element={<PredictionsPage />} />
        <Route path="/standings"  element={<StandingsPage />} />
        <Route path="/results"    element={<ResultsPage />} />
      </Routes>
    </div>
  )
}