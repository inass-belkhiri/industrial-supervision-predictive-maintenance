// App.jsx — Root component with dark/light theme toggle

import React, { useState, useEffect, useRef, useMemo } from 'react'
import { useWebSocket } from './hooks/useWebSocket'
import SupervisionTab  from './components/SupervisionTab'
import DiagnosticTab   from './components/DiagnosticTab'
import MaintenanceTab  from './components/MaintenanceTab'

const TABS = [
  { id: 'supervision', label: 'Supervision' },
  { id: 'diagnostic',  label: 'Diagnostic Intelligent' },
  { id: 'maintenance', label: 'Maintenance Predictive' },
]
const MAX_HISTORY = 600

// ── Sun icon ───────────────────────────────────────────────────────────
function SunIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="5"/>
      <line x1="12" y1="1" x2="12" y2="3"/>
      <line x1="12" y1="21" x2="12" y2="23"/>
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
      <line x1="1" y1="12" x2="3" y2="12"/>
      <line x1="21" y1="12" x2="23" y2="12"/>
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>
  )
}

// ── Moon icon ──────────────────────────────────────────────────────────
function MoonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
    </svg>
  )
}

export default function App() {
  const [activeTab, setActiveTab] = useState('supervision')
  const [theme, setTheme]         = useState('dark')   // 'dark' | 'light'
  const { data, connected }       = useWebSocket()
  const historyRef = useRef({})
  const [sensors, setSensors]     = useState([])

  // Apply theme to root element
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark')

  useEffect(() => {
    if (!data?.sensors) return
    data.sensors.forEach(s => {
      const key = `${s.group_id}-${s.mold_id}`
      if (!historyRef.current[key]) historyRef.current[key] = []
      const arr = historyRef.current[key]
      if (s.temperature != null) {
        arr.push(s.temperature)
        if (arr.length > MAX_HISTORY) arr.splice(0, arr.length - MAX_HISTORY)
      }
    })
    setSensors(
      data.sensors.map(s => ({
        ...s,
        history: [...(historyRef.current[`${s.group_id}-${s.mold_id}`] ?? [])],
      }))
    )
  }, [data])

  const [clock, setClock] = useState('')
  useEffect(() => {
    const tick = () => setClock(new Date().toLocaleTimeString('fr-FR'))
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  const alertCount = useMemo(
    () => sensors.filter(s => s.status === 'ALERTE').length,
    [sensors]
  )

  return (
    <div className="min-h-screen flex flex-col" data-theme={theme}>

      {/* ── Top bar ────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 flex items-center gap-6 px-8 py-4"
        style={{
          background:           'var(--bg-header)',
          backdropFilter:       'blur(24px)',
          WebkitBackdropFilter: 'blur(24px)',
          borderBottom:         '1px solid var(--header-border)',
          boxShadow:            '0 1px 0 rgba(139,92,246,0.1), 0 4px 24px rgba(0,0,0,0.15)',
        }}
      >
        {/* Logo + title */}
        <div className="flex items-center gap-3 mr-4">
          <div className="flex flex-col gap-0.5">
            <div className="flex gap-0.5">
              {[0,1,2].map(i => (
                <div key={i} className="w-1.5 h-3 rounded-sm"
                  style={{ background: `rgba(99,102,241,${0.5 + i * 0.25})` }} />
              ))}
            </div>
            <div className="flex gap-0.5">
              {[0,1,2].map(i => (
                <div key={i} className="w-1.5 h-1.5 rounded-sm"
                  style={{ background: `rgba(139,92,246,${0.4 + i * 0.2})` }} />
              ))}
            </div>
          </div>
          <div>
            <div className="text-sm font-bold leading-tight" style={{ color: 'var(--text-primary)' }}>
              Supervision Thermique
            </div>
            <div className="text-xs leading-tight" style={{ color: 'var(--text-muted)' }}>
              Industrielle -- Yazaki ENSA
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex items-center gap-1 rounded-2xl p-1"
          style={{
            background: 'var(--bg-nav)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            border: '1px solid var(--border-nav)',
          }}>
          {TABS.map(tab => (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`nav-btn ${activeTab === tab.id ? 'nav-btn-active' : 'nav-btn-inactive'}`}>
              {tab.label}
              {tab.id === 'diagnostic' && alertCount > 0 && (
                <span className="ml-2 inline-flex items-center justify-center w-4 h-4 text-xs font-bold bg-red-500 text-white rounded-full">
                  {alertCount}
                </span>
              )}
            </button>
          ))}
        </nav>

        {/* Right side */}
        <div className="ml-auto flex items-center gap-3">

          {/* Theme toggle */}
          <button className="theme-toggle" onClick={toggleTheme}
            title={theme === 'dark' ? 'Passer en mode clair' : 'Passer en mode sombre'}>
            {theme === 'dark' ? <SunIcon /> : <MoonIcon />}
          </button>

          {/* Connection status */}
          <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400' : 'bg-red-400 blink'}`} />
            {connected ? 'Connecte' : 'Deconnecte'}
          </div>

          {alertCount > 0 && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-500/15 border border-red-500/30">
              <div className="w-2 h-2 rounded-full bg-red-400 blink" />
              <span className="text-xs font-medium text-red-400">
                {alertCount} alerte{alertCount > 1 ? 's' : ''}
              </span>
            </div>
          )}

          <div className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>{clock}</div>
        </div>
      </header>

      {/* ── Main content ───────────────────────────────────── */}
      <main className="flex-1 px-8 py-6">
        {activeTab === 'supervision' && <SupervisionTab sensors={sensors} />}
        {activeTab === 'diagnostic'  && <DiagnosticTab  diagnostic={data?.diagnostic ?? null} />}
        {activeTab === 'maintenance' && <MaintenanceTab  maintenance={data?.maintenance ?? []} />}
      </main>

      {/* ── Footer ─────────────────────────────────────────── */}
      <footer className="px-8 py-3 flex items-center justify-between text-xs"
        style={{ color: 'var(--text-muted)', borderTop: '1px solid var(--border-card)' }}>
        <span>
          Supervision Thermique Industrielle -- Diagnostic Intelligent des Causes et Maintenance Predictive de l&apos;Encrassement par Soft Sensing et Machine Learning
        </span>
        <span>ENSA Kenitra -- Yazaki -- 2025-2026</span>
      </footer>
    </div>
  )
}

