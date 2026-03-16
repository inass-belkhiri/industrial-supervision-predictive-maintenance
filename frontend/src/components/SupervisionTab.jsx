// SupervisionTab.jsx
// Renders 4 heater groups, each with 3 mold cards.
// Groups are laid out side by side in a 4-column grid.
// No horizontal scrollbar — all 12 cards visible at once.

import React, { useMemo } from 'react'
import MoldCard from './MoldCard'

const GROUP_NAMES = {
  1: 'Heater 1',
  2: 'Heater 2',
  3: 'Heater 3',
  4: 'Heater 4',
}

// Status priority for group badge
const STATUS_PRIORITY = { ERREUR: 3, ALERTE: 2, OK: 1 }

function GroupBadge({ sensors }) {
  const worst = sensors.reduce((acc, s) => {
    return (STATUS_PRIORITY[s.status] ?? 0) > (STATUS_PRIORITY[acc] ?? 0) ? s.status : acc
  }, 'OK')

  const styles = {
    OK:     'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    ALERTE: 'bg-red-500/15 text-red-400 border-red-500/30',
    ERREUR: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  }

  const labels = { OK: 'Normal', ALERTE: 'Alerte', ERREUR: 'Erreur' }

  return (
    <span className={`text-xs font-medium px-2.5 py-1 rounded-full border ${styles[worst]}`}>
      {labels[worst]}
    </span>
  )
}

function HeaterGroup({ groupId, sensors }) {
  const avgTemp = useMemo(() => {
    const valid = sensors.filter(s => s.temperature != null)
    if (!valid.length) return null
    return valid.reduce((sum, s) => sum + s.temperature, 0) / valid.length
  }, [sensors])

  return (
    <div className="flex flex-col gap-3">
      {/* Group header */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-indigo-500 shadow-sm shadow-indigo-500/50" />
          <span className="text-sm font-semibold text-slate-200">
            {GROUP_NAMES[groupId] ?? `Groupe ${groupId}`}
          </span>
          {avgTemp != null && (
            <span className="text-xs text-slate-500">
              moy. {avgTemp.toFixed(1)} deg C
            </span>
          )}
        </div>
        <GroupBadge sensors={sensors} />
      </div>

      {/* Divider */}
      <div style={{ height: 1, background: 'linear-gradient(to right, rgba(139,92,246,0.4), rgba(139,92,246,0.1), transparent)' }} />

      {/* 3 mold cards stacked vertically within the group column */}
      <div className="flex flex-col gap-3">
        {sensors.map(mold => (
          <MoldCard key={`${mold.group_id}-${mold.mold_id}`} mold={mold} />
        ))}
        {sensors.length === 0 && (
          <div className="card p-6 text-center text-slate-600 text-sm">
            Aucun capteur detecte
          </div>
        )}
      </div>
    </div>
  )
}

export default function SupervisionTab({ sensors = [] }) {
  // Group sensors by group_id
  const groups = useMemo(() => {
    const map = { 1: [], 2: [], 3: [], 4: [] }
    sensors.forEach(s => {
      const gid = s.group_id
      if (map[gid]) map[gid].push(s)
    })
    return map
  }, [sensors])

  const totalAlerts = useMemo(
    () => sensors.filter(s => s.status === 'ALERTE').length,
    [sensors]
  )

  return (
    <div className="flex flex-col gap-6 fade-in">

      {/* Summary bar */}
      <div className="flex items-center gap-6 px-1">
        <div className="flex items-center gap-2">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          <span className="text-sm text-slate-400">
            {sensors.filter(s => s.status === 'OK').length} moules normaux
          </span>
        </div>
        {totalAlerts > 0 && (
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 rounded-full bg-red-500 blink" />
            <span className="text-sm text-red-400 font-medium">
              {totalAlerts} alerte{totalAlerts > 1 ? 's' : ''} active{totalAlerts > 1 ? 's' : ''}
            </span>
          </div>
        )}
        <div className="ml-auto text-xs text-slate-600">
          Acquisition : 1 Hz -- 12 capteurs MODBUS RTU RS485
        </div>
      </div>

      {/* 4-column grid — one column per heater group */}
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map(gid => (
          <HeaterGroup key={gid} groupId={gid} sensors={groups[gid]} />
        ))}
      </div>
    </div>
  )
}

