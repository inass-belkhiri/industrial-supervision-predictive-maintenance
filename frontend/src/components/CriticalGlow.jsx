import React from 'react'

export default function CriticalGlow({ active }) {
  return (
    <>
      <div
        aria-hidden="true"
        style={{
          position: 'fixed',
          inset: 0,
          pointerEvents: 'none',
          zIndex: 9999,
          opacity: active ? 1 : 0,
          transition: 'opacity 0.6s ease',
          animation: active ? 'criticalEdgePulse 1.5s ease-in-out infinite' : 'none',
        }}
      />
      <style>{`
        @keyframes criticalEdgePulse {
          0%, 100% { box-shadow: inset 0 0 70px 6px rgba(220,40,50,0.50); }
          50%      { box-shadow: inset 0 0 140px 22px rgba(245,55,65,0.85); }
        }
      `}</style>
    </>
  )
}
