// MaintenanceTab.jsx

import React, { useMemo } from 'react'

// ── Urgency config (couleurs via variables CSS pour adaptation au thème) ─
const URGENCY_CONFIG = {
  OK:     { label: 'Propre',     color: 'var(--color-ok)',     bg: 'var(--bg-ok)',     border: 'var(--border-ok)'     },
  FAIBLE: { label: 'Surveiller', color: 'var(--color-faible)', bg: 'var(--bg-faible)', border: 'var(--border-faible)' },
  MOYEN:  { label: 'Planifier',  color: 'var(--color-moyen)',  bg: 'var(--bg-moyen)',  border: 'var(--border-moyen)'  },
  HAUTE:  { label: 'Urgent',     color: 'var(--color-haute)',  bg: 'var(--bg-haute)',  border: 'var(--border-haute)'  },
  URGENT: { label: 'Arreter',    color: 'var(--color-urgent)', bg: 'var(--bg-urgent)', border: 'var(--border-urgent)' },
}

const SHOW_CI = new Set(['MOYEN', 'HAUTE', 'URGENT'])

const DAYS_FR   = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim']
const MONTHS_FR = ['Janvier','Fevrier','Mars','Avril','Mai','Juin',
                   'Juillet','Aout','Septembre','Octobre','Novembre','Decembre']

// ── 3D Red Pin SVG ─────────────────────────────────────────────────────
function Pin3D({ size = 36 }) {
  return (
    <svg width={size} height={size * 1.4} viewBox="0 0 36 50" fill="none">
      <defs>
        <radialGradient id="pinGrad" cx="38%" cy="32%" r="60%">
          <stop offset="0%"   stopColor="#ff6b6b" />
          <stop offset="50%"  stopColor="#ef4444" />
          <stop offset="100%" stopColor="#991b1b" />
        </radialGradient>
        <radialGradient id="pinShine" cx="35%" cy="28%" r="40%">
          <stop offset="0%"   stopColor="rgba(255,255,255,0.55)" />
          <stop offset="100%" stopColor="rgba(255,255,255,0)"    />
        </radialGradient>
        <filter id="pinShadow" x="-40%" y="-40%" width="180%" height="180%">
          <feDropShadow dx="1" dy="3" stdDeviation="2.5" floodColor="#7f1d1d" floodOpacity="0.45"/>
        </filter>
      </defs>
      <line x1="18" y1="26" x2="18" y2="48" stroke="#b91c1c" strokeWidth="2" strokeLinecap="round"/>
      <ellipse cx="18" cy="48" rx="4" ry="1.5" fill="rgba(0,0,0,0.15)"/>
      <circle cx="18" cy="14" r="13" fill="url(#pinGrad)" filter="url(#pinShadow)"/>
      <circle cx="18" cy="14" r="13" fill="url(#pinShine)"/>
      <circle cx="18" cy="14" r="4"  fill="rgba(255,255,255,0.22)"/>
    </svg>
  )
}

// ── Single Calendar (right panel) avec effet 3D et pliure ──────────────
function MainCalendar({ targetMold }) {
  const hasDate = targetMold?.predicted_date != null
  const cfg     = targetMold ? (URGENCY_CONFIG[targetMold.urgence] ?? URGENCY_CONFIG.OK) : URGENCY_CONFIG.OK
  const showCI  = targetMold && SHOW_CI.has(targetMold.urgence)

  const targetDate = useMemo(() => {
    if (!hasDate) return null
    const p = targetMold.predicted_date.split('/')
    if (p.length === 3) return new Date(+p[2], +p[1] - 1, +p[0])
    return null
  }, [targetMold])

  const displayDate   = targetDate ?? new Date()
  const year          = displayDate.getFullYear()
  const month         = displayDate.getMonth()
  const targetDay     = targetDate ? targetDate.getDate() : null
  const firstDay      = new Date(year, month, 1)
  let   startOffset   = firstDay.getDay() - 1
  if (startOffset < 0) startOffset = 6
  const daysInMonth   = new Date(year, month + 1, 0).getDate()
  const today         = new Date()
  const todayDay      = today.getDate()
  const isCurrentMonth = today.getMonth() === month && today.getFullYear() === year

  const cells = []
  for (let i = 0; i < startOffset; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)

  return (
    <div className="calendar-3d" style={{
      position: 'relative',
      background: 'var(--calendar-bg)',
      border: '1px solid var(--calendar-border)',
      borderRadius: 20,
      overflow: 'visible',
      boxShadow: 'var(--shadow-card)',
    }}>
      {/* En-tête avec épingle 3D */}
      <div style={{
        background: 'var(--calendar-header)',
        borderBottom: '1px solid var(--calendar-border)',
        borderRadius: '20px 20px 0 0',
        padding: '18px 22px',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        position: 'relative',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Pin3D size={28} />
          <span style={{
            fontWeight: 800, fontSize: 18,
            color: 'var(--text-primary)', letterSpacing: '-0.3px',
          }}>
            {MONTHS_FR[month]} {year}
          </span>
        </div>
        {hasDate ? (
          <span style={{
            fontSize: 12, fontWeight: 700, padding: '4px 14px', borderRadius: 20,
            background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}`,
          }}>
            J-{targetMold.jours_maintenance}
          </span>
        ) : (
          <span style={{
            fontSize: 12, fontWeight: 600, padding: '4px 14px', borderRadius: 20,
            background: 'rgba(99,102,241,0.08)', color: 'var(--text-muted)',
            border: '1px solid rgba(99,102,241,0.15)',
          }}>
            En attente
          </span>
        )}
      </div>

      {/* Jours de la semaine */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(7,1fr)',
        padding: '14px 18px 6px', gap: 4,
      }}>
        {DAYS_FR.map(d => (
          <div key={d} style={{
            textAlign: 'center', fontSize: 10, fontWeight: 700,
            color: 'var(--text-muted)', padding: '4px 0',
            textTransform: 'uppercase', letterSpacing: '0.07em',
          }}>{d}</div>
        ))}
      </div>

      {/* Grille des jours */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(7,1fr)',
        padding: '4px 18px 20px', gap: 4,
      }}>
        {cells.map((day, i) => {
          const isTarget = day !== null && day === targetDay
          const isToday  = isCurrentMonth && day === todayDay
          return (
            <div key={i} style={{
              position: 'relative',
              height: 40,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              borderRadius: 10,
              fontSize: 13,
              fontWeight: isTarget || isToday ? 800 : 400,
              color: isTarget
                ? '#ffffff'
                : isToday ? '#6366f1'
                : day ? 'var(--text-secondary)' : 'transparent',
              background: isTarget
                ? cfg.color
                : isToday ? 'rgba(99,102,241,0.12)' : 'transparent',
              border: isTarget
                ? `2px solid ${cfg.color}`
                : isToday ? '2px solid rgba(99,102,241,0.35)' : '2px solid transparent',
              boxShadow: isTarget ? `0 4px 14px ${cfg.bg}` : 'none',
              overflow: 'visible',
            }}>
              {day || ''}
              {isTarget && (
                <div style={{
                  position: 'absolute', top: -46, left: '50%',
                  transform: 'translateX(-50%)',
                  zIndex: 20, pointerEvents: 'none',
                }}>
                  <Pin3D size={34} />
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* Message d'attente avec contour circulaire */}
      {!hasDate ? (
        <div className="attention-circle" style={{
          margin: '0 18px 18px', padding: '16px 18px', borderRadius: 50,
          background: 'rgba(99,102,241,0.05)',
          border: '3px dashed #ef4444',
          boxShadow: '0 0 15px rgba(239,68,68,0.3)',
          textAlign: 'center',
          animation: 'pulse 2s infinite',
        }}>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 600, marginBottom: 4 }}>
            Date en attente de calcul
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', opacity: 0.9 }}>
            Le modèle Ridge nécessite 7 jours de données
          </div>
        </div>
      ) : (
        <div style={{
          margin: '0 18px 18px', padding: '16px 18px', borderRadius: 14,
          background: cfg.bg, border: `1.5px solid ${cfg.border}`,
        }}>
          <div style={{
            fontSize: 10, color: 'var(--text-muted)', marginBottom: 6,
            fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em',
          }}>
            Maintenance recommandée — Moule {targetMold.mold_id} · Groupe {targetMold.group_id}
          </div>
          <div style={{
            fontSize: 28, fontWeight: 900, color: cfg.color,
            letterSpacing: '-1px', lineHeight: 1,
          }}>
            {targetMold.predicted_date}
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8 }}>
            Dans{' '}
            <strong style={{ color: cfg.color }}>{targetMold.jours_maintenance} jours</strong>
            {' '}— planifier le détartrage
          </div>

          {showCI && targetMold.borne_basse != null && (
            <div style={{
              marginTop: 12, paddingTop: 10,
              borderTop: `1px solid ${cfg.border}`,
              display: 'flex', gap: 16,
            }}>
              <div>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Pire cas (IC 90%)
                </div>
                <div style={{ fontSize: 16, fontWeight: 800, color: cfg.color }}>
                  J-{targetMold.borne_basse}
                </div>
              </div>
              <div style={{ width: 1, background: cfg.border }} />
              <div>
                <div style={{ fontSize: 9, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Meilleur cas
                </div>
                <div style={{ fontSize: 16, fontWeight: 800, color: cfg.color }}>
                  J-{targetMold.borne_haute}
                </div>
              </div>
              <div style={{ fontSize: 9, color: 'var(--text-muted)', alignSelf: 'flex-end', marginLeft: 'auto' }}>
                Bootstrap · 1000 sim.
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Degradation bar ────────────────────────────────────────────────────
function DegradationBar({ pct, urgency }) {
  const cfg     = URGENCY_CONFIG[urgency] ?? URGENCY_CONFIG.OK
  const clamped = Math.min(Math.max(pct ?? 0, 0), 100)
  const segments = [
    { end: 20,  color: '#10b981' },
    { end: 53,  color: '#38bdf8' },
    { end: 80,  color: '#f59e0b' },
    { end: 100, color: '#ef4444' },
  ]
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
      <div style={{
        flex: 1, height: 5, borderRadius: 99, overflow: 'hidden',
        display: 'flex', background: 'rgba(100,116,139,0.12)',
      }}>
        {segments.map((seg, i) => {
          const segStart = i === 0 ? 0 : segments[i-1].end
          const segWidth = seg.end - segStart
          const filled   = Math.min(Math.max(clamped - segStart, 0), segWidth)
          return (
            <div key={i} style={{ width: `${segWidth}%`, height: '100%', overflow: 'hidden' }}>
              <div style={{
                height: '100%', width: `${(filled/segWidth)*100}%`,
                background: seg.color, transition: 'width 0.7s ease',
              }} />
            </div>
          )
        })}
      </div>
      <span style={{
        fontSize: 10, fontWeight: 700, color: cfg.color,
        minWidth: 28, textAlign: 'right',
      }}>
        {clamped.toFixed(0)}%
      </span>
    </div>
  )
}

// ── Mold row ─────────────────────────────
function MoldRow({ mold, isSelected, onClick }) {
  const {
    mold_id, position,
    epaisseur_mm, delta_T_calcaire,
    jours_maintenance, urgence, degradation_pct,
  } = mold

  const cfg      = URGENCY_CONFIG[urgence] ?? URGENCY_CONFIG.OK
  const posLabel = { gauche:'Gauche', centre:'Centre', droite:'Droite' }[position] ?? position
  const showDeg  = urgence !== 'OK'

  return (
    <div
      onClick={onClick}
      style={{
        padding: '8px 10px', borderRadius: 8, cursor: 'pointer',
        border: isSelected ? `1.5px solid ${cfg.color}` : '1.5px solid transparent',
        background: isSelected ? cfg.bg : 'transparent',
        transition: 'all 0.18s',
        display: 'flex', flexDirection: 'column', gap: 6,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
            Moule {mold_id}
          </span>
          <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 6 }}>
            {posLabel}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {jours_maintenance != null && (
            <span style={{
              fontSize: 10, fontWeight: 700, color: cfg.color,
              background: cfg.bg, border: `1px solid ${cfg.border}`,
              padding: '2px 8px', borderRadius: 99,
            }}>
              J-{jours_maintenance}
            </span>
          )}
          <span style={{
            fontSize: 10, fontWeight: 600, padding: '2px 8px', borderRadius: 99,
            color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.border}`,
          }}>
            {cfg.label}
          </span>
        </div>
      </div>

      {showDeg && <DegradationBar pct={degradation_pct} urgency={urgence} />}

      <div style={{ display: 'flex', gap: 16 }}>
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          Épaisseur{' '}
          <strong style={{ color: 'var(--text-secondary)', fontWeight: 700 }}>
            {epaisseur_mm != null ? `${epaisseur_mm.toFixed(2)} mm` : '--'}
          </strong>
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          ΔT calcaire{' '}
          <strong style={{ color: 'var(--text-secondary)', fontWeight: 700 }}>
            {delta_T_calcaire != null ? `${delta_T_calcaire.toFixed(2)} °C` : '--'}
          </strong>
        </div>
      </div>
    </div>
  )
}

// ── Heater group block ─
function HeaterGroup({ groupId, molds, selectedId, onSelect }) {
  const worstUrgency = useMemo(() => {
    const order = { URGENT:5, HAUTE:4, MOYEN:3, FAIBLE:2, OK:1 }
    return molds.reduce(
      (w, m) => (order[m.urgence]??0) > (order[w]??0) ? m.urgence : w, 'OK'
    )
  }, [molds])

  const cfg = URGENCY_CONFIG[worstUrgency] ?? URGENCY_CONFIG.OK

  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--heater-border-outer)',
      borderRadius: 16,
      overflow: 'hidden',
      boxShadow: 'var(--shadow-card)',
    }}>
      <div style={{
        padding: '10px 14px',
        background: 'var(--calendar-header)',
        borderBottom: '1px solid var(--heater-border-outer)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <div style={{
          width: 8, height: 8, borderRadius: '50%',
          background: cfg.color,
          boxShadow: `0 0 8px ${cfg.color}`,
        }} />
        <span style={{
          fontSize: 13, fontWeight: 800, color: 'var(--text-primary)',
        }}>
          Heater {groupId}
        </span>
      </div>

      <div style={{ padding: '8px' }}>
        {molds.map(m => (
          <MoldRow
            key={m.mold_id}
            mold={m}
            isSelected={selectedId === m.mold_id}
            onClick={() => onSelect(m)}
          />
        ))}
        {molds.length === 0 && (
          <div style={{
            padding: '20px', textAlign: 'center',
            fontSize: 12, color: 'var(--text-muted)',
          }}>
            En attente des capteurs...
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main tab ───────────────────────────────────────────────────────────
export default function MaintenanceTab({ maintenance = [] }) {
  const URGENCY_ORDER = { URGENT:5, HAUTE:4, MOYEN:3, FAIBLE:2, OK:1 }

  const mostUrgent = useMemo(() => {
    if (!maintenance.length) return null
    return [...maintenance].sort(
      (a, b) => (URGENCY_ORDER[b.urgence]??0) - (URGENCY_ORDER[a.urgence]??0)
    )[0]
  }, [maintenance])

  const [selectedMold, setSelectedMold] = React.useState(null)
  const calendarMold = selectedMold ?? mostUrgent

  const groups = useMemo(() => {
    const map = { 1:[], 2:[], 3:[], 4:[] }
    if (!maintenance.length) {
      const pos = ['gauche','centre','droite']
      ;[1,2,3,4].forEach(gid =>
        pos.forEach((p, j) => map[gid].push({
          mold_id: gid*3-2+j, group_id: gid, position: p, urgence: 'OK', degradation_pct: 0,
        }))
      )
      return map
    }
    maintenance.forEach(m => { if (map[m.group_id]) map[m.group_id].push(m) })
    return map
  }, [maintenance])

  const criticalCount = maintenance.filter(m => SHOW_CI.has(m.urgence)).length

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:8 }} className="fade-in">

      {/* Barre de résumé avec police plus grande */}
      <div className="card-glass" style={{
        padding: '12px 20px',
        display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 20,
      }}>
        {[
          { label: 'Modèle',              value: 'Grey-box + Ridge + Bootstrap',  color: 'var(--text-primary)' },
          { label: 'Intervalle IC',        value: '90% (percentiles 5-95)',        color: 'var(--text-primary)' },
          { label: 'Moules à maintenir',  value: `${criticalCount} / ${maintenance.length || 12}`, color: '#f97316' },
        ].map(item => (
          <div key={item.label}>
            <div style={{
              fontSize: 11, color: 'var(--text-muted)', marginBottom: 4,
              textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600,
            }}>
              {item.label}
            </div>
            <div style={{ fontSize: 14, fontWeight: 700, color: item.color }}>
              {item.value}
            </div>
          </div>
        ))}
      </div>

      {/* Layout principal */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 300px', gap:8, alignItems:'start' }}>

        {/* LEFT — 2×2 heater groups */}
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:8 }}>
          {[1,2,3,4].map(gid => (
            <HeaterGroup
              key={gid}
              groupId={gid}
              molds={groups[gid] ?? []}
              selectedId={calendarMold?.mold_id}
              onSelect={m => setSelectedMold(prev =>
                prev?.mold_id === m.mold_id ? null : m
              )}
            />
          ))}
        </div>

        {/* RIGHT — calendar */}
        <div style={{ position:'sticky', top:70 }}>
          <MainCalendar targetMold={calendarMold} />
        </div>
      </div>
    </div>
  )
}
