// CircularGauge.jsx
// SVG circular gauge showing temperature as a colored arc.
// Props:
//   value    : current temperature (float)
//   min      : minimum scale value (default 35)
//   max      : maximum scale value (default 50)
//   status   : "OK" | "ALERTE" | "ERREUR"
//   size     : diameter in pixels (default 90)

import React from 'react'

const STATUS_COLORS = {
  OK:     '#34d399',   // emerald
  ALERTE: '#f87171',   // red
  ERREUR: '#fbbf24',   // amber
}

export default function CircularGauge({ value, min = 35, max = 50, status = 'OK', size = 90 }) {
  const radius      = (size - 14) / 2
  const cx          = size / 2
  const cy          = size / 2
  const startAngle  = -220   // degrees, measured from 3-o'clock
  const endAngle    = 40
  const totalAngle  = 360 - Math.abs(startAngle) + endAngle  // 220 + 40 = 260 degrees

  const toRad = (deg) => (deg * Math.PI) / 180

  // Arc path helper
  const describeArc = (start, end) => {
    const s  = toRad(start - 90)
    const e  = toRad(end - 90)
    const x1 = cx + radius * Math.cos(s)
    const y1 = cy + radius * Math.sin(s)
    const x2 = cx + radius * Math.cos(e)
    const y2 = cy + radius * Math.sin(e)
    const large = end - start > 180 ? 1 : 0
    return `M ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2}`
  }

  // Clamp value and compute fill percentage
  const clamped = Math.min(Math.max(value ?? min, min), max)
  const pct     = (clamped - min) / (max - min)
  const fillEnd = startAngle + totalAngle * pct
  const color   = STATUS_COLORS[status] ?? STATUS_COLORS.OK

  const trackPath = describeArc(startAngle, endAngle)
  const fillPath  = pct > 0.001 ? describeArc(startAngle, fillEnd) : null

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {/* Track */}
      <path
        d={trackPath}
        fill="none"
        stroke="#1e2540"
        strokeWidth="7"
        strokeLinecap="round"
      />
      {/* Fill */}
      {fillPath && (
        <path
          d={fillPath}
          fill="none"
          stroke={color}
          strokeWidth="7"
          strokeLinecap="round"
          style={{ filter: `drop-shadow(0 0 4px ${color}55)` }}
        />
      )}
      {/* Center text */}
      <text
        x={cx}
        y={cy - 4}
        textAnchor="middle"
        dominantBaseline="middle"
        fill={color}
        fontSize="14"
        fontWeight="700"
        fontFamily="Inter, sans-serif"
      >
        {value != null ? value.toFixed(1) : '--'}
      </text>
      <text
        x={cx}
        y={cy + 12}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="#64748b"
        fontSize="9"
        fontFamily="Inter, sans-serif"
      >
        deg C
      </text>
    </svg>
  )
}
