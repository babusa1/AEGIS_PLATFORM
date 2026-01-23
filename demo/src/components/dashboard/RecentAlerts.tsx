'use client'

import { AlertTriangle, Clock, DollarSign, FileX } from 'lucide-react'
import clsx from 'clsx'

const alerts = [
  {
    id: 1,
    type: 'critical',
    title: 'High-value denial approaching deadline',
    description: 'Claim #CLM-2024-8847 ($45,230) appeal due in 3 days',
    time: '2 hours ago',
    icon: AlertTriangle,
  },
  {
    id: 2,
    type: 'warning',
    title: 'Cardiology denial spike detected',
    description: 'AEGIS detected 23% increase in cardiology denials this week',
    time: '4 hours ago',
    icon: FileX,
  },
  {
    id: 3,
    type: 'info',
    title: 'Appeal deadline reminder',
    description: '5 claims require appeal submission within 7 days',
    time: '6 hours ago',
    icon: Clock,
  },
  {
    id: 4,
    type: 'success',
    title: 'Appeal won - funds recovered',
    description: 'Claim #CLM-2024-7821 appeal approved: $12,450 recovered',
    time: '1 day ago',
    icon: DollarSign,
  },
]

const typeStyles = {
  critical: 'bg-red-50 text-red-600 border-red-200',
  warning: 'bg-yellow-50 text-yellow-600 border-yellow-200',
  info: 'bg-blue-50 text-blue-600 border-blue-200',
  success: 'bg-green-50 text-green-600 border-green-200',
}

export function RecentAlerts() {
  return (
    <div className="space-y-3">
      {alerts.map((alert) => (
        <div 
          key={alert.id}
          className={clsx(
            'p-4 rounded-lg border cursor-pointer transition-all hover:shadow-sm',
            typeStyles[alert.type as keyof typeof typeStyles]
          )}
        >
          <div className="flex items-start gap-3">
            <alert.icon className="w-5 h-5 mt-0.5" />
            <div className="flex-1 min-w-0">
              <h4 className="font-medium text-gray-900 text-sm">{alert.title}</h4>
              <p className="text-gray-600 text-sm mt-1">{alert.description}</p>
              <p className="text-gray-400 text-xs mt-2">{alert.time}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
