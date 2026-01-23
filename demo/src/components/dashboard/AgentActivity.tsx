'use client'

import { Bot, CheckCircle, Clock, Loader2 } from 'lucide-react'
import clsx from 'clsx'

const activities = [
  {
    id: 1,
    agent: 'Unified View Agent',
    action: 'Generated Patient 360 for MRN-78234',
    status: 'completed',
    time: '2 min ago',
    confidence: 0.94,
  },
  {
    id: 2,
    agent: 'Action Agent',
    action: 'Drafting appeal for Claim #CLM-2024-9012',
    status: 'in_progress',
    time: 'Running...',
    confidence: null,
  },
  {
    id: 3,
    agent: 'Insight Agent',
    action: 'Analyzing denial patterns for Cardiology',
    status: 'in_progress',
    time: 'Running...',
    confidence: null,
  },
  {
    id: 4,
    agent: 'Action Agent',
    action: 'Generated appeal for Claim #CLM-2024-8901',
    status: 'completed',
    time: '15 min ago',
    confidence: 0.87,
  },
  {
    id: 5,
    agent: 'Insight Agent',
    action: 'Discovered revenue leakage pattern',
    status: 'completed',
    time: '1 hour ago',
    confidence: 0.82,
  },
]

const statusIcons = {
  completed: CheckCircle,
  in_progress: Loader2,
  pending: Clock,
}

const statusColors = {
  completed: 'text-green-500',
  in_progress: 'text-blue-500',
  pending: 'text-gray-400',
}

export function AgentActivity() {
  return (
    <div className="space-y-4">
      {activities.map((activity) => {
        const StatusIcon = statusIcons[activity.status as keyof typeof statusIcons]
        
        return (
          <div key={activity.id} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
            <div className="w-8 h-8 bg-aegis-primary/10 rounded-lg flex items-center justify-center">
              <Bot className="w-4 h-4 text-aegis-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h4 className="font-medium text-gray-900 text-sm">{activity.agent}</h4>
                <StatusIcon 
                  className={clsx(
                    'w-4 h-4',
                    statusColors[activity.status as keyof typeof statusColors],
                    activity.status === 'in_progress' && 'animate-spin'
                  )} 
                />
              </div>
              <p className="text-gray-600 text-sm mt-0.5">{activity.action}</p>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-gray-400 text-xs">{activity.time}</span>
                {activity.confidence && (
                  <span className="text-xs text-green-600 bg-green-50 px-2 py-0.5 rounded">
                    {Math.round(activity.confidence * 100)}% confidence
                  </span>
                )}
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
