// MoldCard.jsx
// Displays one mold sensor card with:
//   - mold_id, position label
//   - CircularGauge showing current temperature
//   - Mini sparkline chart (last 10 minutes of readings)
//   - Status badge and timestamp

import React, { useMemo } from 'react'
import { LineChart, Line, ResponsiveContainer, Tooltip, ReferenceLine } from 'recharts'
import CircularGauge from './CircularGauge'

const POSITION_LABELS = {
  gauche:  'Gauche',
  centre:  'Centre',
  droite:  'Droite',
}

const STATUS_LABELS = {
  OK:     'Normal',
  ALERTE: 'Alerte',
  ERREUR: 'Erreur',
}

const CustomTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--card-bg)', backdropFilter: 'blur(12px)', border: '1px solid var(--card-border)', borderRadius: 8, padding: '4px 8px', fontSize: 11, color: 'var(--text-primary)' }}>
      {payload[0].value?.toFixed(2)} deg C
    </div>
  )
}

export default function MoldCard({ mold }) {
  const {
    mold_id,
    group_id,
    position,
    temperature,
    status,
    history = [],
    timestamp,
    deviation,
    threshold,
  } = mold

  // Determine card border accent color by status
  const borderColor = {
    OK:     'border-l-emerald-500',
    ALERTE: 'border-l-red-500',
    ERREUR: 'border-l-amber-500',
  }[status] ?? 'border-l-slate-600'

  // Prepare sparkline data (keep last 600 points = 10 min at 1Hz)
  const sparkData = useMemo(() => {
    const slice = history.slice(-600)
    return slice.map((val, i) => ({ t: i, v: val }))
  }, [history])

  const formattedTime = useMemo(() => {
    if (!timestamp) return '--'
    try {
      const d = new Date(timestamp)
      return d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    } catch { return '--' }
  }, [timestamp])

  const devColor = deviation != null
    ? deviation >= 0 ? 'text-emerald-400' : 'text-red-400'
    : 'text-slate-400'

  return (
    <div className={`border-l-4 ${borderColor} p-4 flex flex-col gap-3 fade-in`}
      style={{ background: "var(--card-bg)", backdropFilter: "var(--card-blur)", WebkitBackdropFilter: "var(--card-blur)", border: "1px solid var(--card-border)", borderRadius: 18, boxShadow: "var(--card-shadow)" }}>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Moule {mold_id}
          </span>
          <div className="text-xs text-slate-500 mt-0.5">
            {POSITION_LABELS[position] ?? position}
          </div>
        </div>
        <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${
          status === 'OK'
            ? 'status-ok'
            : status === 'ALERTE'
              ? 'status-alert'
              : 'status-error'
        } ${status === 'ALERTE' ? 'blink' : ''}`}>
          {STATUS_LABELS[status] ?? status}
        </span>
      </div>

      {/* Temperature — big bold number */}
      <div className="flex items-center justify-between px-1">
        <div>
          <div className="text-xs text-slate-500 mb-0.5">Temperature</div>
          <div className={`text-3xl font-black tabular-nums leading-none ${
            status === 'ALERTE' ? 'text-red-400' :
            status === 'ERREUR' ? 'text-amber-400' : ''
          }`}
          style={status === 'OK' ? { color: 'var(--temp-normal)' } : {}}>
            {temperature != null ? temperature.toFixed(1) : '--'}
            <span className="text-base font-semibold text-slate-400 ml-1">°C</span>
          </div>
        </div>
        <div className="flex flex-col items-end gap-1">
          <div className="text-xs text-slate-500">Ecart</div>
          <div className={`text-sm font-bold ${devColor}`}>
            {deviation != null
              ? `${deviation >= 0 ? '+' : ''}${deviation.toFixed(2)} °C`
              : '--'}
          </div>
        </div>
      </div>

      {/* Gauge + metrics */}
      <div className="flex items-center gap-4">
        <CircularGauge
          value={temperature}
          min={35}
          max={50}
          status={status}
          size={88}
        />
        <div className="flex flex-col gap-2 flex-1">
          <div>
            <div className="text-xs text-slate-500">Consigne</div>
            <div className="text-sm font-semibold text-slate-200">
              {threshold != null ? `${threshold.toFixed(1)} deg C` : '45.0 deg C'}
            </div>
          </div>
          <div>
            <div className="text-xs text-slate-500">Seuil critique</div>
            <div className="text-sm font-semibold text-red-400/70">42.0 deg C</div>
          </div>
        </div>
      </div>

      {/* Sparkline — last 10 minutes */}
      <div>
        <div className="text-xs text-slate-500 mb-1">Dernières 10 minutes</div>
        <div className="h-14 w-full">
          {sparkData.length > 1 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={sparkData}>
                <ReferenceLine y={45} stroke="#4f46e5" strokeDasharray="3 2" strokeWidth={1} />
                <ReferenceLine y={42} stroke="#ef4444" strokeDasharray="3 2" strokeWidth={1} />
                <Line
                  type="monotone"
                  dataKey="v"
                  stroke={status === 'ALERTE' ? '#f87171' : '#818cf8'}
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
                <Tooltip content={<CustomTooltip />} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center text-xs text-slate-600">
              En attente de données...
            </div>
          )}
        </div>
      </div>

      {/* Timestamp */}
      <div style={{ fontSize: 10, color: 'var(--text-muted)', textAlign: 'right', borderTop: '1px solid var(--card-border)', paddingTop: 8 }}>
        {formattedTime}
      </div>
    </div>
  )
}

