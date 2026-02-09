'use client'

import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, FileText } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  artifacts?: string[]
}

interface ChatPaneProps {
  sessionId: string
  messages: Message[]
  sendMessage: (message: string) => void
  onArtifactSelect: (artifactId: string) => void
}

export function ChatPane({ sessionId, messages, sendMessage, onArtifactSelect }: ChatPaneProps) {
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim()) {
      sendMessage(input)
      setInput('')
    }
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Chat Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Collaboration</h2>
        <p className="text-sm text-gray-500">Work with Librarian, Guardian, Scribe, and Scout agents</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Bot className="w-12 h-12 mx-auto mb-4 text-gray-400" />
            <p>Start collaborating with AI agents</p>
            <p className="text-sm mt-2">Ask questions, request artifacts, or review recommendations</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-3 ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.role !== 'user' && (
                <div className="w-8 h-8 bg-aegis-primary rounded-full flex items-center justify-center flex-shrink-0">
                  <Bot className="w-5 h-5 text-white" />
                </div>
              )}
              <div
                className={`max-w-[70%] rounded-lg p-4 ${
                  message.role === 'user'
                    ? 'bg-aegis-primary text-white'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                {message.artifacts && message.artifacts.length > 0 && (
                  <div className="mt-3 space-y-2">
                    {message.artifacts.map((artifactId) => (
                      <button
                        key={artifactId}
                        onClick={() => onArtifactSelect(artifactId)}
                        className="flex items-center gap-2 px-3 py-2 bg-white/20 rounded text-sm hover:bg-white/30 transition-colors"
                      >
                        <FileText className="w-4 h-4" />
                        <span>View Artifact</span>
                      </button>
                    ))}
                  </div>
                )}
                <p className="text-xs opacity-70 mt-2">{message.timestamp}</p>
              </div>
              {message.role === 'user' && (
                <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center flex-shrink-0">
                  <User className="w-5 h-5 text-gray-600" />
                </div>
              )}
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="px-6 py-4 border-t border-gray-200">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-aegis-primary"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-aegis-primary text-white rounded-lg hover:bg-aegis-primary/90 transition-colors"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </form>
    </div>
  )
}
