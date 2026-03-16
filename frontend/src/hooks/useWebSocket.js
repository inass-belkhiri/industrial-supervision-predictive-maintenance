// useWebSocket.js
// Manages the WebSocket connection to the FastAPI backend.
// Handles automatic reconnection with exponential backoff.
// Returns the latest data object and the connection status.

import { useState, useEffect, useRef, useCallback } from 'react'

const WS_URL = 'ws://localhost:8000/ws'

export function useWebSocket() {
  const [data, setData]           = useState(null)
  const [connected, setConnected] = useState(false)
  const wsRef                     = useRef(null)
  const retryDelay                = useRef(1000)
  const retryTimer                = useRef(null)

  const connect = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => {
      setConnected(true)
      retryDelay.current = 1000
    }

    ws.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        setData(parsed)
      } catch (err) {
        console.error('WebSocket parse error:', err)
      }
    }

    ws.onclose = () => {
      setConnected(false)
      // Exponential backoff: 1s, 2s, 4s, 8s, max 30s
      retryTimer.current = setTimeout(() => {
        retryDelay.current = Math.min(retryDelay.current * 2, 30000)
        connect()
      }, retryDelay.current)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(retryTimer.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [connect])

  return { data, connected }
}
