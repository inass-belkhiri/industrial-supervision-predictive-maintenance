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
  NORMAL:             'Fonctionnement normal',
  POMPE_DEFAILLANTE:  'Pompe defaillante',
  BULLES_AIR:         'Bulles d\'air dans le circuit',
  NIVEAU_BAS:         'Niveau d\'eau bas / Vanne',
  CALCAIRE:           'Encrassement calcaire',
}

const CAUSE_COLORS = {
  NORMAL:             '#34d399',
  POMPE_DEFAILLANTE:  '#f87171',
  BULLES_AIR:         '#60a5fa',
  NIVEAU_BAS:         '#fbbf24',
  CALCAIRE:           '#c084fc',
}

const CAUSE_ACTIONS = {
  POMPE_DEFAILLANTE: [
    'Verifier l\'alimentation electrique de la pompe',
    'Controler le condensateur de demarrage',
    'Inspecter l\'impeller (roue de pompe)',
    'Verifier le pressostat et la soupape',
  ],
  BULLES_AIR: [
    'Purger le circuit hydraulique principal',
    'Verifier les joints des moules affectes',
    'Controler les raccords sur la ligne de retour',
    'Verifier le niveau d\'eau dans le heater',
  ],
  NIVEAU_BAS: [
    'Verifier le niveau d\'eau dans le heater',
    'Controler l\'ouverture de la vanne d\'alimentation',
    'Inspecter les capteurs de niveau',
    'Rechercher une fuite sur le circuit',
  ],
  CALCAIRE: [
    'Planifier un detartrage chimique',
    'Commander les produits de detartrage',
    'Consulter l\'onglet Maintenance Predictive',
    'Verifier la concentration de l\'additif anti-calcaire',
  ],
  NORMAL: [
    'Aucune action requise',
    'Continuer la surveillance en temps reel',
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
  } = diagnostic ?? {}

  const causeLabel  = CAUSE_LABELS[cause]  ?? cause
  const causeColor  = CAUSE_COLORS[cause]  ?? '#94a3b8'
  const actions     = CAUSE_ACTIONS[cause] ?? CAUSE_ACTIONS.NORMAL

  const formattedTime = useMemo(() => {
    if (!timestamp) return '--'
    try {
      return new Date(timestamp).toLocaleString('fr-FR')
    } catch { return '--' }
  }, [timestamp])

  return (
    <div className="flex flex-col gap-6 fade-in">

      {/* Status banner */}
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
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Derniere analyse : {formattedTime}
          </p>
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
          <h3 className="text-sm font-semibold text-slate-300">
            Actions recommandees
          </h3>
          <div className="flex flex-wrap gap-4 items-start pt-2" style={{ position: 'relative' }}>
            {actions.map((action, i) => (
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
                <span className="text-slate-500 text-xs">
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

