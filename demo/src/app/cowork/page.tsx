'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Plus, Users, Clock, FileText, MessageSquare } from 'lucide-react'

interface CoworkSession {
  id: string
  patient_id: string
  patient_name: string
  status: 'active' | 'pending' | 'completed'
  participants: number
  last_activity: string
  artifacts_count: number
}

export default function CoworkPage() {
  const [sessions, setSessions] = useState<CoworkSession[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Fetch Cowork sessions from API
    fetch('/api/v1/cowork/sessions')
      .then(res => res.json())
      .then(data => {
        setSessions(data.sessions || [])
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch sessions:', err)
        setLoading(false)
      })
  }, [])

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Cowork Sessions</h1>
          <p className="text-gray-600 mt-1">Collaborative clinical workspace with AI agents</p>
        </div>
        <Link
          href="/cowork/new"
          className="flex items-center gap-2 px-4 py-2 bg-aegis-primary text-white rounded-lg hover:bg-aegis-primary/90 transition-colors"
        >
          <Plus className="w-5 h-5" />
          New Session
        </Link>
      </div>

      {/* Active Sessions */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Active Sessions</h2>
        {loading ? (
          <div className="text-center py-12 text-gray-500">Loading sessions...</div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-300">
            <MessageSquare className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600 mb-2">No active Cowork sessions</p>
            <p className="text-sm text-gray-500">Start a new session to collaborate with AI agents</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {sessions.map((session) => (
              <Link
                key={session.id}
                href={`/cowork/${session.id}`}
                className="block p-6 bg-white rounded-lg border border-gray-200 hover:border-aegis-primary hover:shadow-lg transition-all"
              >
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="font-semibold text-gray-900">{session.patient_name}</h3>
                    <p className="text-sm text-gray-500">Patient ID: {session.patient_id}</p>
                  </div>
                  <span
                    className={`px-2 py-1 text-xs rounded-full ${
                      session.status === 'active'
                        ? 'bg-green-100 text-green-800'
                        : session.status === 'pending'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {session.status}
                  </span>
                </div>

                <div className="flex items-center gap-4 text-sm text-gray-600">
                  <div className="flex items-center gap-1">
                    <Users className="w-4 h-4" />
                    <span>{session.participants} participants</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <FileText className="w-4 h-4" />
                    <span>{session.artifacts_count} artifacts</span>
                  </div>
                </div>

                <div className="mt-4 pt-4 border-t border-gray-200">
                  <div className="flex items-center gap-1 text-xs text-gray-500">
                    <Clock className="w-3 h-3" />
                    <span>Last activity: {session.last_activity}</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
