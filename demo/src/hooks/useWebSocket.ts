import { useState, useEffect, useRef } from 'react'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  artifacts?: string[]
}

export function useWebSocket(url: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    const ws = new WebSocket(url)

    ws.onopen = () => {
      setIsConnected(true)
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'message') {
        setMessages((prev) => [...prev, data.message])
      } else if (data.type === 'artifact_update') {
        // Handle artifact updates
      } else if (data.type === 'state_sync') {
        // Handle state synchronization
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      setIsConnected(false)
      console.log('WebSocket disconnected')
    }

    wsRef.current = ws

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [url])

  const sendMessage = (content: string) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: 'message',
          content,
        })
      )
      // Optimistically add user message
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: 'user',
          content,
          timestamp: new Date().toISOString(),
        },
      ])
    }
  }

  return { messages, sendMessage, isConnected }
}
