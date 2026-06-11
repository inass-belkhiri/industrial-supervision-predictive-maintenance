// useWebSocket.js
// Manages the WebSocket connection to the FastAPI backend.
// Handles automatic reconnection with exponential backoff.
// Returns the latest data object and the connection status.

import { useState, useEffect, useRef, useCallback } from 'react'

const WS_URL = '/ws'

export function useWebSocket() {
  const [data, setData]           = useState(null)
  const [connected, setConnected] = useState(false)
  const wsRef                     = useRef(null)
  const retryDelay                = useRef(1000)
  const retryTimer                = useRef(null)

  const reconnectRef = useRef(true)

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
        if (parsed && parsed.t === 'ping') return
        setData(parsed)
      } catch (err) {
        console.error('WebSocket parse error:', err)
      }
    }

    ws.onclose = () => {
      setConnected(false)
      if (!reconnectRef.current) return
      retryTimer.current = setTimeout(() => {
        retryDelay.current = Math.min(retryDelay.current * 2, 30000)
        if (reconnectRef.current) connect()
      }, retryDelay.current)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  useEffect(() => {
    reconnectRef.current = true
    connect()
    return () => {
      reconnectRef.current = false
      clearTimeout(retryTimer.current)
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
      }
    }
  }, [connect])

  return { data, connected }
}
