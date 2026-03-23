// DiagnosticTab.jsx
// Shows the intelligent diagnostic results from Isolation Forest + Random Forest.
// Displays:
//   - Overall anomaly status
//   - Detected cause with confidence level
//   - Affected molds list
//   - Recommended actions as post-it cards
//   - Confidence interval visualization

import React, { useMemo } from 'react'

// Post-it color palette — one color per action item
const POSTIT_COLORS = [
  { bg: '#fef9c3', text: '#713f12', pin: '#f59e0b' },   // yellow
  { bg: '#dbeafe', text: '#1e3a5f', pin: '#3b82f6' },   // blue
  { bg: '#fce7f3', text: '#701a3e', pin: '#ec4899' },   // pink
  { bg: '#d1fae5', text: '#064e3b', pin: '#10b981' },   // green
  { bg: '#ede9fe', text: '#3b0764', pin: '#8b5cf6' },   // purple
]

function PinIcon({ color }) {
  return (
    <svg width="18" height="24" viewBox="0 0 18 24" fill="none">
      <ellipse cx="9" cy="8" rx="6" ry="6" fill={color} />
      <ellipse cx="9" cy="8" rx="3.5" ry="3.5" fill="rgba(255,255,255,0.5)" />
      <rect x="8" y="14" width="2" height="10" rx="1" fill={color} opacity="0.7" />
    </svg>
  )
}

function PostItCard({ text, index }) {
  const theme = POSTIT_COLORS[index % POSTIT_COLORS.length]
  // Subtle random tilt per card
  const tilts = [-1.5, 1.2, -0.8, 1.8, -1.0]
  const tilt  = tilts[index % tilts.length]

  return (
    <div
      className="postit p-4 pt-6 flex flex-col gap-2 min-h-28"
      style={{
        background:    theme.bg,
        transform:     `rotate(${tilt}deg)`,
        minWidth:      '140px',
        maxWidth:      '180px',
        flex:          '1 1 140px',
      }}
    >
      {/* Pin */}
      <div className="absolute -top-3 left-1/2 -translate-x-1/2">
        <PinIcon color={theme.pin} />
      </div>
      <p
        className="text-sm font-medium leading-snug"
        style={{ color: theme.text }}
      >
        {text}
      </p>
      <div
        className="mt-auto text-xs font-semibold opacity-60"
        style={{ color: theme.text }}
      >
        Action {index + 1}
      </div>
    </div>
  )
}

function ConfidenceBar({ value, color }) {
  return (
    <div className="w-full">
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>Confiance du modele</span>
        <span className="font-bold" style={{ color }}>{(value * 100).toFixed(0)}%</span>
      </div>
      <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${value * 100}%`, background: color }}
        />
      </div>
    </div>
  )
}

const CAUSE_LABELS = {
  CALCAIRE_TUYAUX:           'Encrassement calcaire des tuyaux',
  HEATER_POMPE_HS:           'Pompe heater hors service',
  HEATER_RESISTANCE_HS:      'Resistance heater hors service',
  NIVEAU_BAS_VANNE_PANNE:    'Niveau bas / Vanne en panne',
  BULLES_AIR:                'Bulles d\'air dans le circuit',
  FUITE_CIRCUIT:             'Fuite sur le circuit hydraulique',
  ISOLATION_DEGRADEE:        'Isolation thermique degradee',
}

const CAUSE_COLORS = {
  CALCAIRE_TUYAUX:           '#c084fc',  // purple
  HEATER_POMPE_HS:           '#f87171',  // red
  HEATER_RESISTANCE_HS:      '#ef4444',  // dark red
  NIVEAU_BAS_VANNE_PANNE:    '#fbbf24',  // amber
  BULLES_AIR:                '#60a5fa',  // blue
  FUITE_CIRCUIT:             '#f97316',  // orange
  ISOLATION_DEGRADEE:        '#a78bfa',  // light purple
}

const CAUSE_ACTIONS = {
  CALCAIRE_TUYAUX: [
    'Verifier niveau et dosage de l\'additif anti-calcaire',
    'Controler le systeme de dosage automatique de l\'additif',
    'Consulter l\'onglet Maintenance Predictive pour la date de detartrage planifiee',
    'Si debit < seuil critique : Planifier detartrage chimique immediatement',
    'Surveiller evolution debit toutes les 4h',
  ],
  HEATER_POMPE_HS: [
    'Verifier debit pompe heater (nominal: 16.5 L/min)',
    'Ecouter bruits anormaux/vibrations pompe',
    'Verifier alimentation electrique pompe',
    'Inspecter roue pompe (usure, blocage, cavitation)',
  ],
  HEATER_RESISTANCE_HS: [
    'Mesurer T_heater (doit etre 45°C ± 1°C)',
    'Verifier alimentation electrique resistance',
    'Tester continuite resistance (multimetre)',
    'Verifier regulation temperature PID',
  ],
  NIVEAU_BAS_VANNE_PANNE: [
    'Verifier niveau reservoir visuellement',
    'Tester vanne appoint manuellement',
    'Verifier commande electrique vanne (automate)',
  ],
  BULLES_AIR: [
    'Purger circuit hydraulique immediatement',
    'Verifier niveau reservoir (doit etre > 50%)',
    'Inspecter joints pompe',
    'Surveiller stabilite temperature 30 min post-purge',
  ],
  FUITE_CIRCUIT: [
    'Inspecter visuellement circuit complet',
    'Rechercher fuites (joints, raccords, tuyaux)',
    'Mesurer pression circuit si possible',
    'Reparer fuite identifiee',
  ],
  ISOLATION_DEGRADEE: [
    'Inspecter isolation moule visuellement',
  ],
}

function AffectedMoldsChip({ moldIds = [] }) {
  if (!moldIds.length) return null
  return (
    <div className="flex flex-wrap gap-2">
      {moldIds.map(id => (
        <span
          key={id}
          className="text-xs font-medium px-2 py-0.5 rounded bg-red-500/15 text-red-400 border border-red-500/20"
        >
          Moule {id}
        </span>
      ))}
    </div>
  )
}

export default function DiagnosticTab({ diagnostic = null }) {
  const {
    anomaly_detected = false,
    cause            = 'NORMAL',
    confidence       = 1.0,
    affected_molds   = [],
    anomaly_score    = null,
    timestamp        = null,
    features         = {},
    // AMDEC fields from backend
    amdec_criticite  = null,
    amdec_priorite   = null,
    actions          = null,
  } = diagnostic ?? {}

  const causeLabel  = CAUSE_LABELS[cause] ?? cause
  const causeColor  = CAUSE_COLORS[cause] ?? '#94a3b8'
  // Use actions from backend if available, otherwise use static CAUSE_ACTIONS
  const actionsList = actions ?? (CAUSE_ACTIONS[cause] || ['Aucune action requise'])

  const formattedTime = useMemo(() => {
    if (!timestamp) return '--'
    try {
      return new Date(timestamp).toLocaleString('fr-FR')
    } catch { return '--' }
  }, [timestamp])

  // Helper to get criticite color
  const getCriticiteColor = (criticite) => {
    if (criticite >= 120) return '#ef4444'  // red - very critical
    if (criticite >= 60) return '#f97316'   // orange - critical
    if (criticite >= 30) return '#fbbf24'   // amber - moderate
    return '#22c55e'  // green - low
  }

  const criticiteColor = amdec_criticite ? getCriticiteColor(amdec_criticite) : null

  return (
    <div className="flex flex-col gap-6 fade-in">

      {/* Status banner with AMDEC info */}
      <div
        className="card-glass p-5 flex items-start gap-5"
        style={{ borderColor: `${causeColor}33` }}
      >
        {/* Indicator dot */}
        <div className="mt-1 flex-shrink-0">
          <div
            className="w-4 h-4 rounded-full"
            style={{
              background:    causeColor,
              boxShadow:     `0 0 10px ${causeColor}66`,
              animation:     anomaly_detected ? 'blink-anim 1s step-end infinite' : 'none',
            }}
          />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h2 className="text-lg font-bold text-slate-100">
              {anomaly_detected ? 'Anomalie Detectee' : 'Etat Normal'}
            </h2>
            <span
              className="text-xs font-semibold px-3 py-1 rounded-full border"
              style={{ color: causeColor, borderColor: `${causeColor}44`, background: `${causeColor}18` }}
            >
              {causeLabel}
            </span>
            {/* AMDEC Priority Badge */}
            {amdec_priorite != null && (
              <span
                className="text-xs font-bold px-3 py-1 rounded-full border"
                style={{
                  color: criticiteColor,
                  borderColor: `${criticiteColor}44`,
                  background: `${criticiteColor}18`
                }}
              >
                Priorite AMDEC: {amdec_priorite}/7
              </span>
            )}
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Derniere analyse : {formattedTime}
          </p>

          {/* AMDEC Criticite Bar */}
          {amdec_criticite != null && (
            <div className="mt-3">
              <div className="flex items-center gap-3">
                <span className="text-xs text-slate-500">Criticite AMDEC:</span>
                <div className="flex-1 max-w-xs">
                  <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${Math.min((amdec_criticite / 200) * 100, 100)}%`,
                        background: criticiteColor,
                      }}
                    />
                  </div>
                </div>
                <span className="text-xs font-bold" style={{ color: criticiteColor }}>
                  {amdec_criticite} (G×O×D)
                </span>
              </div>
            </div>
          )}

          {affected_molds.length > 0 && (
            <div className="mt-3">
              <div className="text-xs text-slate-500 mb-2">Moules affectes</div>
              <AffectedMoldsChip moldIds={affected_molds} />
            </div>
          )}
        </div>
      </div>

      {/* Two columns: confidence + features | post-it actions */}
      <div className="grid grid-cols-2 gap-6">

        {/* Left: confidence details */}
        <div className="card p-5 flex flex-col gap-5">
          <h3 className="text-sm font-semibold text-slate-300">
            Niveau de confiance du diagnostic
          </h3>

          <ConfidenceBar value={confidence} color={causeColor} />

          {anomaly_score != null && (
            <div>
              <div className="text-xs text-slate-500 mb-1">Score d\'anomalie (Isolation Forest)</div>
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 bg-slate-800 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700 bg-violet-500"
                    style={{ width: `${Math.abs(Math.min(anomaly_score, 0)) * 100 * 3}%` }}
                  />
                </div>
                <span className="text-xs font-mono text-violet-400">
                  {anomaly_score.toFixed(3)}
                </span>
              </div>
              <div className="text-xs text-slate-600 mt-1">
                {anomaly_score > -0.1 ? 'Normal' : anomaly_score > -0.3 ? 'Suspect' : 'Anomalie confirmee'}
              </div>
            </div>
          )}

          {/* Signature features */}
          {Object.keys(features).length > 0 && (
            <div>
              <div className="text-xs text-slate-500 mb-2">Signature detectee</div>
              <div className="flex flex-col gap-1.5">
                {Object.entries(features).map(([key, val]) => (
                  <div key={key} className="flex justify-between text-xs">
                    <span className="text-slate-500">{key.replace(/_/g, ' ')}</span>
                    <span className="text-slate-300 font-mono">
                      {typeof val === 'number' ? val.toFixed(3) : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: post-it recommended actions */}
        <div className="card p-5 flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-300">
              Actions recommandees
            </h3>
            {amdec_priorite != null && (
              <span className="text-xs text-slate-500">
                {actionsList.length} action(s)
              </span>
            )}
          </div>
          <div className="flex flex-wrap gap-4 items-start pt-2" style={{ position: 'relative' }}>
            {actionsList.map((action, i) => (
              <PostItCard key={i} text={action} index={i} />
            ))}
          </div>
        </div>
      </div>

      {/* History log (last 5 events) */}
      {diagnostic?.history?.length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-3">
            Historique des evenements recents
          </h3>
          <div className="flex flex-col gap-2">
            {diagnostic.history.slice(-5).reverse().map((evt, i) => (
              <div key={i} className="flex items-center gap-3 text-sm py-2 border-b border-slate-800 last:border-0">
                <div
                  className="w-2 h-2 flex-shrink-0 rounded-full"
                  style={{ background: CAUSE_COLORS[evt.cause] ?? '#64748b' }}
                />
                <span className="text-slate-400 w-40 flex-shrink-0 text-xs font-mono">
                  {evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString('fr-FR') : '--'}
                </span>
                <span className="text-slate-300 flex-1">
                  {CAUSE_LABELS[evt.cause] ?? evt.cause}
                </span>
                {/* AMDEC priority in history */}
                {evt.amdec_priorite != null && (
                  <span
                    className="text-xs font-medium px-2 py-0.5 rounded"
                    style={{
                      background: `${getCriticiteColor(evt.amdec_criticite ?? 0)}22`,
                      color: getCriticiteColor(evt.amdec_criticite ?? 0),
                    }}
                  >
                    P{evt.amdec_priorite}
                  </span>
                )}
                <span className="text-slate-500 text-xs w-10 text-right">
                  {evt.confidence != null ? `${(evt.confidence * 100).toFixed(0)}%` : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

