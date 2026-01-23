'use client'

import { useState } from 'react'
import { Search, Filter, AlertCircle, Clock, DollarSign, PenTool, ChevronRight } from 'lucide-react'

const denials = [
  { 
    id: 'D001', 
    claimNumber: 'CLM-2024-8847', 
    patient: 'John Smith',
    mrn: 'MRN-78234',
    payer: 'Blue Cross',
    denialReason: 'PR-204 Medical Necessity',
    category: 'medical_necessity',
    deniedAmount: 45230,
    serviceDate: '2024-01-05',
    denialDate: '2024-01-15',
    appealDeadline: '2024-02-15',
    daysToDeadline: 3,
    status: 'pending',
    priority: 'critical',
  },
  { 
    id: 'D002', 
    claimNumber: 'CLM-2024-8901', 
    patient: 'Robert Johnson',
    mrn: 'MRN-78236',
    payer: 'Medicare',
    denialReason: 'CO-4 Coding Error',
    category: 'coding',
    deniedAmount: 12450,
    serviceDate: '2024-01-08',
    denialDate: '2024-01-18',
    appealDeadline: '2024-03-18',
    daysToDeadline: 35,
    status: 'in_progress',
    priority: 'high',
  },
  { 
    id: 'D003', 
    claimNumber: 'CLM-2024-9012', 
    patient: 'Maria Garcia',
    mrn: 'MRN-78235',
    payer: 'Aetna',
    denialReason: 'PR-15 Authorization Required',
    category: 'authorization',
    deniedAmount: 8750,
    serviceDate: '2024-01-10',
    denialDate: '2024-01-17',
    appealDeadline: '2024-02-17',
    daysToDeadline: 5,
    status: 'pending',
    priority: 'high',
  },
  { 
    id: 'D004', 
    claimNumber: 'CLM-2024-7821', 
    patient: 'Emily Davis',
    mrn: 'MRN-78237',
    payer: 'United',
    denialReason: 'CO-16 Missing Information',
    category: 'documentation',
    deniedAmount: 3200,
    serviceDate: '2023-12-20',
    denialDate: '2024-01-05',
    appealDeadline: '2024-03-05',
    daysToDeadline: 22,
    status: 'pending',
    priority: 'medium',
  },
]

const priorityColors = {
  critical: 'bg-red-100 text-red-700 border-red-200',
  high: 'bg-orange-100 text-orange-700 border-orange-200',
  medium: 'bg-yellow-100 text-yellow-700 border-yellow-200',
  low: 'bg-green-100 text-green-700 border-green-200',
}

const statusColors = {
  pending: 'bg-gray-100 text-gray-700',
  in_progress: 'bg-blue-100 text-blue-700',
  appealed: 'bg-purple-100 text-purple-700',
  won: 'bg-green-100 text-green-700',
  lost: 'bg-red-100 text-red-700',
}

export default function DenialsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedDenial, setSelectedDenial] = useState<string | null>(null)

  const totalDenied = denials.reduce((sum, d) => sum + d.deniedAmount, 0)
  const urgentCount = denials.filter(d => d.daysToDeadline <= 7).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Denial Management</h1>
          <p className="text-gray-500 mt-1">Review and appeal denied claims</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-aegis-primary text-white rounded-lg hover:bg-aegis-primary/90">
          <PenTool className="w-4 h-4" />
          Bulk Appeal
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card bg-red-50 border-red-100">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-8 h-8 text-red-500" />
            <div>
              <p className="text-sm text-red-600">Total Denied</p>
              <p className="text-2xl font-bold text-red-700">${totalDenied.toLocaleString()}</p>
            </div>
          </div>
        </div>
        <div className="card bg-orange-50 border-orange-100">
          <div className="flex items-center gap-3">
            <Clock className="w-8 h-8 text-orange-500" />
            <div>
              <p className="text-sm text-orange-600">Urgent (≤7 days)</p>
              <p className="text-2xl font-bold text-orange-700">{urgentCount}</p>
            </div>
          </div>
        </div>
        <div className="card bg-blue-50 border-blue-100">
          <div className="flex items-center gap-3">
            <PenTool className="w-8 h-8 text-blue-500" />
            <div>
              <p className="text-sm text-blue-600">Pending Review</p>
              <p className="text-2xl font-bold text-blue-700">{denials.filter(d => d.status === 'pending').length}</p>
            </div>
          </div>
        </div>
        <div className="card bg-green-50 border-green-100">
          <div className="flex items-center gap-3">
            <DollarSign className="w-8 h-8 text-green-500" />
            <div>
              <p className="text-sm text-green-600">Win Rate (YTD)</p>
              <p className="text-2xl font-bold text-green-700">68%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by claim number, patient, or reason..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-aegis-primary/20"
          />
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50">
          <Filter className="w-4 h-4" />
          Filters
        </button>
      </div>

      {/* Denial List */}
      <div className="space-y-3">
        {denials.map((denial) => (
          <div 
            key={denial.id}
            className={`card card-hover cursor-pointer border-l-4 ${
              denial.priority === 'critical' ? 'border-l-red-500' :
              denial.priority === 'high' ? 'border-l-orange-500' :
              denial.priority === 'medium' ? 'border-l-yellow-500' :
              'border-l-green-500'
            }`}
            onClick={() => setSelectedDenial(denial.id)}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <span className="font-mono font-medium text-aegis-primary">{denial.claimNumber}</span>
                  <span className={`badge ${priorityColors[denial.priority as keyof typeof priorityColors]}`}>
                    {denial.priority}
                  </span>
                  <span className={`badge ${statusColors[denial.status as keyof typeof statusColors]}`}>
                    {denial.status.replace('_', ' ')}
                  </span>
                </div>
                <div className="flex items-center gap-6 text-sm text-gray-600">
                  <span><strong>Patient:</strong> {denial.patient} ({denial.mrn})</span>
                  <span><strong>Payer:</strong> {denial.payer}</span>
                  <span><strong>Service Date:</strong> {denial.serviceDate}</span>
                </div>
                <div className="mt-2 p-2 bg-gray-50 rounded text-sm">
                  <strong>Denial Reason:</strong> {denial.denialReason}
                </div>
              </div>
              <div className="text-right ml-6">
                <p className="text-2xl font-bold text-red-600">${denial.deniedAmount.toLocaleString()}</p>
                <p className={`text-sm mt-1 ${denial.daysToDeadline <= 7 ? 'text-red-600 font-medium' : 'text-gray-500'}`}>
                  {denial.daysToDeadline <= 7 ? `⚠️ ${denial.daysToDeadline} days to deadline` : `${denial.daysToDeadline} days to deadline`}
                </p>
                <button 
                  className="mt-3 flex items-center gap-1 text-aegis-primary text-sm font-medium hover:underline"
                  onClick={(e) => {
                    e.stopPropagation()
                    // Navigate to appeal generation
                  }}
                >
                  Generate Appeal <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
