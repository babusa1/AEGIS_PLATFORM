'use client'

import { useState } from 'react'
import { 
  Search, 
  Bell, 
  MessageSquare,
  Sparkles
} from 'lucide-react'

export function Header() {
  const [showAIChat, setShowAIChat] = useState(false)

  return (
    <header className="h-16 bg-white border-b border-gray-200 px-6 flex items-center justify-between">
      {/* Search */}
      <div className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search patients, claims, or ask VeritOS..."
            className="w-full pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-aegis-primary/20 focus:border-aegis-primary"
          />
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <kbd className="hidden sm:inline-flex px-2 py-0.5 text-xs text-gray-400 bg-gray-100 rounded">
              ⌘K
            </kbd>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-4 ml-4">
        {/* AI Assistant */}
        <button 
          onClick={() => setShowAIChat(!showAIChat)}
          className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-aegis-primary to-aegis-secondary text-white rounded-lg hover:opacity-90 transition-opacity"
        >
          <Sparkles className="w-4 h-4" />
          <span className="text-sm font-medium">Ask VeritOS</span>
        </button>

        {/* Notifications */}
        <button className="relative p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
          <Bell className="w-5 h-5" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>

        {/* Messages */}
        <button className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors">
          <MessageSquare className="w-5 h-5" />
        </button>
      </div>

      {/* AI Chat Panel (simplified) */}
      {showAIChat && (
        <div className="absolute right-6 top-16 w-96 bg-white rounded-xl shadow-xl border border-gray-200 z-50">
          <div className="p-4 border-b border-gray-100">
            <h3 className="font-semibold flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-aegis-primary" />
              VeritOS AI Assistant
            </h3>
          </div>
          <div className="p-4 h-64 overflow-y-auto">
            <div className="bg-gray-50 rounded-lg p-3 mb-3">
              <p className="text-sm text-gray-600">
                Hello! I'm VeritOS, your healthcare intelligence assistant. I can help you:
              </p>
              <ul className="mt-2 text-sm text-gray-600 space-y-1">
                <li>• Generate patient 360 views</li>
                <li>• Draft denial appeals</li>
                <li>• Discover operational insights</li>
                <li>• Answer questions about your data</li>
              </ul>
            </div>
          </div>
          <div className="p-4 border-t border-gray-100">
            <input
              type="text"
              placeholder="Ask me anything..."
              className="w-full px-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-aegis-primary/20"
            />
          </div>
        </div>
      )}
    </header>
  )
}
