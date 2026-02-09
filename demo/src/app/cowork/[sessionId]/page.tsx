'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import { WorkspaceLayout } from '@/components/cowork/WorkspaceLayout'

export default function CoworkSessionPage() {
  const params = useParams()
  const sessionId = params.sessionId as string
  const [session, setSession] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Fetch session details
    fetch(`/api/v1/cowork/sessions/${sessionId}`)
      .then(res => res.json())
      .then(data => {
        setSession(data)
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch session:', err)
        setLoading(false)
      })
  }, [sessionId])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-aegis-primary mx-auto mb-4"></div>
          <p className="text-gray-600">Loading Cowork session...</p>
        </div>
      </div>
    )
  }

  if (!session) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <p className="text-gray-600 mb-2">Session not found</p>
          <a href="/cowork" className="text-aegis-primary hover:underline">
            Back to sessions
          </a>
        </div>
      </div>
    )
  }

  return <WorkspaceLayout sessionId={sessionId} session={session} />
}
