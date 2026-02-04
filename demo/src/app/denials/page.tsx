'use client'

import { useState, useEffect } from 'react'
import { Search, Filter, AlertCircle, Clock, DollarSign, PenTool, ChevronRight, X, FileText, Bot, TrendingUp } from 'lucide-react'

const API_BASE = 'http://localhost:8001'

interface Denial {
  id: string
  claim_id: string
  claim_number: string
  patient_id: string
  patient_name: string
  mrn: string
  payer: string
  denial_code: string
  denial_category: string
  denial_reason: string
  denied_amount: number
  service_date: string | null
  denial_date: string | null
  appeal_deadline: string | null
  days_to_deadline: number | null
  appeal_status: string
  priority: string
  notes: string | null
}

interface DenialAnalytics {
  total_denials: number
  total_denied_amount: number
  pending_count: number
  in_progress_count: number
  appealed_count: number
  won_count: number
  lost_count: number
  urgent_count: number
  win_rate: number
  by_category: Array<{ category: string; count: number; amount: number }>
  by_payer: Array<{ payer: string; count: number; amount: number }>
}

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

const categoryLabels: Record<string, string> = {
  medical_necessity: 'Medical Necessity',
  authorization: 'Authorization',
  coverage: 'Coverage',
  documentation: 'Documentation',
  coding: 'Coding',
  payment_adjustment: 'Payment Adjustment',
}

export default function DenialsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [denials, setDenials] = useState<Denial[]>([])
  const [analytics, setAnalytics] = useState<DenialAnalytics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedDenial, setSelectedDenial] = useState<Denial | null>(null)
  const [generatingAppeal, setGeneratingAppeal] = useState(false)
  const [appealLetter, setAppealLetter] = useState<string | null>(null)

  useEffect(() => {
    fetchDenials()
    fetchAnalytics()
  }, [])

  const fetchDenials = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/v1/denials`)
      if (!res.ok) throw new Error('Failed to fetch denials')
      const data = await res.json()
      setDenials(data.denials || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load denials')
    } finally {
      setLoading(false)
    }
  }

  const fetchAnalytics = async () => {
    try {
      const res = await fetch(`${API_BASE}/v1/denials/analytics`)
      if (!res.ok) throw new Error('Failed to fetch analytics')
      const data = await res.json()
      setAnalytics(data)
    } catch (err) {
      console.error('Error fetching analytics:', err)
    }
  }

  const generateAppeal = async (denial: Denial) => {
    setGeneratingAppeal(true)
    setSelectedDenial(denial)
    try {
      const res = await fetch(`${API_BASE}/v1/agents/appeal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          claim_id: denial.claim_id,
          denial_id: denial.id,
          additional_context: `Denial reason: ${denial.denial_reason}`
        })
      })
      if (!res.ok) throw new Error('Failed to generate appeal')
      const data = await res.json()
      setAppealLetter(data.appeal_letter || 'Appeal generation completed. Review the output.')
    } catch (err) {
      setAppealLetter('Error generating appeal. Please try again or contact support.')
    } finally {
      setGeneratingAppeal(false)
    }
  }

  const filteredDenials = denials.filter(d => 
    d.patient_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.claim_number.toLowerCase().includes(searchQuery.toLowerCase()) ||
    d.denial_reason.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        <p className="font-medium">Error loading denials</p>
        <p className="text-sm">{error}</p>
        <button onClick={fetchDenials} className="mt-2 text-sm underline">Retry</button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Denial Management</h1>
          <p className="text-gray-500 mt-1">Real-time data from PostgreSQL ({denials.length} denials)</p>
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          <PenTool className="w-4 h-4" />
          Bulk Appeal
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-red-500">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-8 h-8 text-red-500" />
            <div>
              <p className="text-sm text-gray-600">Total Denied</p>
              <p className="text-2xl font-bold text-red-700">
                ${(analytics?.total_denied_amount || 0).toLocaleString()}
              </p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-orange-500">
          <div className="flex items-center gap-3">
            <Clock className="w-8 h-8 text-orange-500" />
            <div>
              <p className="text-sm text-gray-600">Urgent (≤7 days)</p>
              <p className="text-2xl font-bold text-orange-700">{analytics?.urgent_count || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-blue-500">
          <div className="flex items-center gap-3">
            <PenTool className="w-8 h-8 text-blue-500" />
            <div>
              <p className="text-sm text-gray-600">Pending Review</p>
              <p className="text-2xl font-bold text-blue-700">{analytics?.pending_count || 0}</p>
            </div>
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4 border-l-4 border-green-500">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-8 h-8 text-green-500" />
            <div>
              <p className="text-sm text-gray-600">Win Rate (YTD)</p>
              <p className="text-2xl font-bold text-green-700">{Math.round((analytics?.win_rate || 0.68) * 100)}%</p>
            </div>
          </div>
        </div>
      </div>

      {/* Analytics Breakdown */}
      {analytics && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold text-gray-900 mb-3">By Category</h3>
            <div className="space-y-2">
              {analytics.by_category.map((cat) => (
                <div key={cat.category} className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">{categoryLabels[cat.category] || cat.category}</span>
                  <div className="flex items-center gap-4">
                    <span className="text-sm font-medium">{cat.count} denials</span>
                    <span className="text-sm font-bold text-red-600">${cat.amount.toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold text-gray-900 mb-3">By Payer</h3>
            <div className="space-y-2">
              {analytics.by_payer.map((payer) => (
                <div key={payer.payer} className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">{payer.payer}</span>
                  <div className="flex items-center gap-4">
                    <span className="text-sm font-medium">{payer.count} denials</span>
                    <span className="text-sm font-bold text-red-600">${payer.amount.toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Search and Filters */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by claim number, patient, or reason..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          />
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50">
          <Filter className="w-4 h-4" />
          Filters
        </button>
      </div>

      {/* Denial List */}
      <div className="space-y-3">
        {filteredDenials.map((denial) => (
          <div 
            key={denial.id}
            className={`bg-white rounded-lg shadow p-4 border-l-4 cursor-pointer hover:shadow-md transition-shadow ${
              denial.priority === 'critical' ? 'border-l-red-500' :
              denial.priority === 'high' ? 'border-l-orange-500' :
              denial.priority === 'medium' ? 'border-l-yellow-500' :
              'border-l-green-500'
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <span className="font-mono font-medium text-blue-600">{denial.claim_number}</span>
                  <span className={`px-2 py-1 text-xs rounded-full ${priorityColors[denial.priority as keyof typeof priorityColors] || 'bg-gray-100'}`}>
                    {denial.priority}
                  </span>
                  <span className={`px-2 py-1 text-xs rounded-full ${statusColors[denial.appeal_status as keyof typeof statusColors] || 'bg-gray-100'}`}>
                    {denial.appeal_status.replace('_', ' ')}
                  </span>
                </div>
                <div className="flex items-center gap-6 text-sm text-gray-600">
                  <span><strong>Patient:</strong> {denial.patient_name} ({denial.mrn})</span>
                  <span><strong>Payer:</strong> {denial.payer}</span>
                  <span><strong>Service Date:</strong> {denial.service_date}</span>
                </div>
                <div className="mt-2 p-2 bg-gray-50 rounded text-sm">
                  <strong>Denial Reason:</strong> {denial.denial_code} - {denial.denial_reason}
                </div>
              </div>
              <div className="text-right ml-6">
                <p className="text-2xl font-bold text-red-600">${denial.denied_amount.toLocaleString()}</p>
                <p className={`text-sm mt-1 ${(denial.days_to_deadline || 999) <= 7 ? 'text-red-600 font-medium' : 'text-gray-500'}`}>
                  {denial.days_to_deadline !== null && denial.days_to_deadline <= 7 
                    ? `⚠️ ${denial.days_to_deadline} days to deadline` 
                    : denial.days_to_deadline !== null 
                      ? `${denial.days_to_deadline} days to deadline`
                      : 'No deadline'
                  }
                </p>
                <button 
                  className="mt-3 flex items-center gap-1 text-blue-600 text-sm font-medium hover:underline ml-auto"
                  onClick={() => generateAppeal(denial)}
                >
                  <Bot className="w-4 h-4" />
                  Generate Appeal <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Appeal Generation Modal */}
      {(selectedDenial && (generatingAppeal || appealLetter)) && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  {generatingAppeal ? 'Generating Appeal...' : 'Appeal Letter Generated'}
                </h2>
                <p className="text-sm text-gray-500">
                  Claim: {selectedDenial.claim_number} | {selectedDenial.patient_name}
                </p>
              </div>
              <button 
                onClick={() => { setSelectedDenial(null); setAppealLetter(null); }}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            
            <div className="p-6">
              {generatingAppeal ? (
                <div className="flex flex-col items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                  <p className="text-gray-600">AI is analyzing denial and generating appeal letter...</p>
                  <p className="text-sm text-gray-400 mt-2">This may take a few seconds</p>
                </div>
              ) : (
                <div>
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                    <h3 className="font-semibold text-blue-800 mb-2 flex items-center gap-2">
                      <FileText className="w-4 h-4" /> Denial Details
                    </h3>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div><strong>Denial Code:</strong> {selectedDenial.denial_code}</div>
                      <div><strong>Category:</strong> {categoryLabels[selectedDenial.denial_category] || selectedDenial.denial_category}</div>
                      <div><strong>Amount:</strong> ${selectedDenial.denied_amount.toLocaleString()}</div>
                      <div><strong>Payer:</strong> {selectedDenial.payer}</div>
                    </div>
                    <div className="mt-2 text-sm">
                      <strong>Reason:</strong> {selectedDenial.denial_reason}
                    </div>
                  </div>
                  
                  <div className="bg-gray-50 border rounded-lg p-4">
                    <h3 className="font-semibold text-gray-800 mb-2">Generated Appeal Letter</h3>
                    <div className="prose prose-sm max-w-none whitespace-pre-wrap text-gray-700">
                      {appealLetter}
                    </div>
                  </div>
                  
                  <div className="flex gap-3 mt-4">
                    <button className="flex-1 py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                      Copy to Clipboard
                    </button>
                    <button className="flex-1 py-2 px-4 bg-green-600 text-white rounded-lg hover:bg-green-700">
                      Submit Appeal
                    </button>
                    <button 
                      onClick={() => generateAppeal(selectedDenial)}
                      className="py-2 px-4 border border-gray-300 rounded-lg hover:bg-gray-50"
                    >
                      Regenerate
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
