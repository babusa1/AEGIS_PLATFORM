'use client'

import { useState, useEffect } from 'react'
import { FileText, Download, Check, X } from 'lucide-react'

interface ArtifactPaneProps {
  artifactId: string
  sessionId: string
}

export function ArtifactPane({ artifactId, sessionId }: ArtifactPaneProps) {
  const [artifact, setArtifact] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [content, setContent] = useState('')

  useEffect(() => {
    fetch(`/api/v1/cowork/sessions/${sessionId}/artifacts/${artifactId}`)
      .then(res => res.json())
      .then(data => {
        setArtifact(data)
        setContent(data.content || '')
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch artifact:', err)
        setLoading(false)
      })
  }, [artifactId, sessionId])

  const handleSave = () => {
    fetch(`/api/v1/cowork/sessions/${sessionId}/artifacts/${artifactId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })
      .then(() => {
        setEditing(false)
      })
      .catch(err => console.error('Failed to save artifact:', err))
  }

  const handleApprove = () => {
    fetch(`/api/v1/cowork/sessions/${sessionId}/artifacts/${artifactId}/approve`, {
      method: 'POST',
    })
      .then(() => {
        // Refresh artifact
      })
      .catch(err => console.error('Failed to approve artifact:', err))
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-3/4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-aegis-primary" />
            <h3 className="font-semibold text-gray-900">{artifact?.type || 'Artifact'}</h3>
          </div>
          <div className="flex items-center gap-2">
            {artifact?.status === 'draft' && (
              <>
                {editing ? (
                  <>
                    <button
                      onClick={handleSave}
                      className="p-2 text-green-600 hover:bg-green-50 rounded"
                    >
                      <Check className="w-5 h-5" />
                    </button>
                    <button
                      onClick={() => {
                        setEditing(false)
                        setContent(artifact.content)
                      }}
                      className="p-2 text-red-600 hover:bg-red-50 rounded"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => setEditing(true)}
                    className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded"
                  >
                    Edit
                  </button>
                )}
                <button
                  onClick={handleApprove}
                  className="px-3 py-1 text-sm bg-green-600 text-white hover:bg-green-700 rounded"
                >
                  Approve
                </button>
              </>
            )}
            <button className="p-2 text-gray-600 hover:bg-gray-100 rounded">
              <Download className="w-5 h-5" />
            </button>
          </div>
        </div>
        <p className="text-xs text-gray-500">
          Created: {artifact?.created_at} • Status: {artifact?.status}
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {editing ? (
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full h-full p-4 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-aegis-primary font-mono text-sm"
          />
        ) : (
          <div className="prose max-w-none">
            <pre className="whitespace-pre-wrap font-mono text-sm bg-gray-50 p-4 rounded-lg">
              {content}
            </pre>
          </div>
        )}
      </div>

      {/* Footer */}
      {artifact?.evidence_links && artifact.evidence_links.length > 0 && (
        <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
          <p className="text-xs font-semibold text-gray-700 mb-2">Evidence Links:</p>
          <div className="space-y-1">
            {artifact.evidence_links.map((link: string, idx: number) => (
              <a
                key={idx}
                href={link}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-aegis-primary hover:underline block"
              >
                {link}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
