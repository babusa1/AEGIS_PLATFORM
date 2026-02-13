'use client'

import Link from 'next/link'
import { 
  Users, 
  FileSearch, 
  PenTool, 
  Lightbulb,
  Upload,
  BarChart3
} from 'lucide-react'

const actions = [
  {
    name: 'Patient 360',
    description: 'Generate unified patient view',
    icon: Users,
    href: '/agents?action=patient-360',
    color: 'bg-blue-500',
  },
  {
    name: 'Review Denials',
    description: 'View claims pending appeal',
    icon: FileSearch,
    href: '/denials',
    color: 'bg-red-500',
  },
  {
    name: 'Draft Appeal',
    description: 'AI-assisted appeal generation',
    icon: PenTool,
    href: '/agents?action=appeal',
    color: 'bg-purple-500',
  },
  {
    name: 'Discover Insights',
    description: 'Find patterns in your data',
    icon: Lightbulb,
    href: '/agents?action=insights',
    color: 'bg-yellow-500',
  },
  {
    name: 'Ingest Data',
    description: 'Upload FHIR or generate synthetic',
    icon: Upload,
    href: '/ingestion',
    color: 'bg-green-500',
  },
  {
    name: 'View Analytics',
    description: 'Denial and revenue reports',
    icon: BarChart3,
    href: '/intelligence',
    color: 'bg-indigo-500',
  },
]

export function QuickActions() {
  return (
    <div className="grid grid-cols-2 gap-3">
      {actions.map((action) => (
        <Link
          key={action.name}
          href={action.href}
          className="p-4 border border-gray-100 rounded-lg hover:border-aegis-primary/30 hover:shadow-sm transition-all group"
        >
          <div className={`w-10 h-10 ${action.color} rounded-lg flex items-center justify-center mb-3 group-hover:scale-110 transition-transform`}>
            <action.icon className="w-5 h-5 text-white" />
          </div>
          <h3 className="font-medium text-gray-900 text-sm">{action.name}</h3>
          <p className="text-gray-500 text-xs mt-1">{action.description}</p>
        </Link>
      ))}
    </div>
  )
}
