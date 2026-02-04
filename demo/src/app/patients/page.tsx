'use client'

import { useState, useEffect } from 'react'
import { Search, Filter, UserCircle, Eye, Bot, X, Activity, Pill, FileText, DollarSign, AlertTriangle } from 'lucide-react'

const API_BASE = 'http://localhost:8001'

interface Patient {
  id: string
  mrn: string
  given_name: string
  family_name: string
  birth_date: string
  gender: string
  phone?: string
  email?: string
  address_city?: string
  address_state?: string
  status?: string
}

interface Patient360 {
  patient: Patient
  conditions: Array<{ id: string; code: string; display: string; status: string }>
  medications: Array<{ id: string; display: string; dosage: string; frequency: string; status: string }>
  encounters: Array<{ id: string; type: string; status: string; admit_date: string }>
  claims: Array<{ id: string; claim_number: string; type: string; status: string; billed_amount: number; paid_amount: number }>
  risk_scores: { overall_score: number; risk_level: string; risk_factors: string[] }
  patient_status: { status: string; label: string; message: string; factors: string[] }
  financial_summary: { total_billed: number; total_paid: number; total_denied: number; collection_rate: string }
}

const riskColors = {
  high: 'bg-red-100 text-red-700',
  moderate: 'bg-yellow-100 text-yellow-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low: 'bg-green-100 text-green-700',
}

const statusColors = {
  RED: 'bg-red-500',
  YELLOW: 'bg-yellow-500',
  GREEN: 'bg-green-500',
}

export default function PatientsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [patients, setPatients] = useState<Patient[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedPatient360, setSelectedPatient360] = useState<Patient360 | null>(null)
  const [loading360, setLoading360] = useState(false)

  useEffect(() => {
    fetchPatients()
  }, [])

  const fetchPatients = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${API_BASE}/v1/patients`)
      if (!res.ok) throw new Error('Failed to fetch patients')
      const data = await res.json()
      setPatients(data.patients || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load patients')
    } finally {
      setLoading(false)
    }
  }

  const fetchPatient360 = async (patientId: string) => {
    try {
      setLoading360(true)
      const res = await fetch(`${API_BASE}/v1/patients/${patientId}`)
      if (!res.ok) throw new Error('Failed to fetch patient details')
      const data = await res.json()
      setSelectedPatient360(data)
    } catch (err) {
      console.error('Error fetching 360:', err)
    } finally {
      setLoading360(false)
    }
  }

  const filteredPatients = patients.filter(p => 
    `${p.given_name} ${p.family_name}`.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.mrn.toLowerCase().includes(searchQuery.toLowerCase())
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
        <p className="font-medium">Error loading patients</p>
        <p className="text-sm">{error}</p>
        <button onClick={fetchPatients} className="mt-2 text-sm underline">Retry</button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Patients</h1>
          <p className="text-gray-500 mt-1">Real-time data from PostgreSQL ({patients.length} patients)</p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="flex gap-4">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search by name or MRN..."
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

      {/* Patient Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Patient</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">MRN</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">DOB</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Location</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
              <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredPatients.map((patient) => (
              <tr key={patient.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                      <UserCircle className="w-6 h-6 text-blue-600" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{patient.given_name} {patient.family_name}</p>
                      <p className="text-sm text-gray-500 capitalize">{patient.gender}</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 font-mono">{patient.mrn}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{patient.birth_date}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{patient.address_city}, {patient.address_state}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 text-xs rounded-full ${patient.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
                    {patient.status || 'active'}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button 
                      onClick={() => fetchPatient360(patient.id)}
                      className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="View Patient 360"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    <button 
                      onClick={() => fetchPatient360(patient.id)}
                      className="p-2 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="Generate AI 360 View"
                    >
                      <Bot className="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Patient 360 Modal */}
      {selectedPatient360 && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex justify-between items-center">
              <div className="flex items-center gap-4">
                <div className={`w-4 h-4 rounded-full ${statusColors[selectedPatient360.patient_status?.status as keyof typeof statusColors] || 'bg-gray-400'}`}></div>
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    {selectedPatient360.patient.given_name} {selectedPatient360.patient.family_name}
                  </h2>
                  <p className="text-sm text-gray-500">
                    {selectedPatient360.patient_status?.label} - {selectedPatient360.patient_status?.message}
                  </p>
                </div>
              </div>
              <button onClick={() => setSelectedPatient360(null)} className="p-2 hover:bg-gray-100 rounded-lg">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-6">
              {/* Patient Info */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500">MRN</p>
                  <p className="font-mono font-medium">{selectedPatient360.patient.mrn}</p>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500">Date of Birth</p>
                  <p className="font-medium">{selectedPatient360.patient.birth_date}</p>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500">Gender</p>
                  <p className="font-medium capitalize">{selectedPatient360.patient.gender}</p>
                </div>
                <div className="bg-gray-50 p-3 rounded-lg">
                  <p className="text-xs text-gray-500">Location</p>
                  <p className="font-medium">{selectedPatient360.patient.address_city}, {selectedPatient360.patient.address_state}</p>
                </div>
              </div>

              {/* Risk Score */}
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-4 rounded-lg">
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-sm text-gray-600 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4" /> Risk Assessment
                    </p>
                    <p className="text-2xl font-bold text-gray-900">
                      {Math.round((selectedPatient360.risk_scores?.overall_score || 0) * 100)}% 
                      <span className={`ml-2 text-sm font-normal px-2 py-1 rounded ${riskColors[selectedPatient360.risk_scores?.risk_level as keyof typeof riskColors] || 'bg-gray-100'}`}>
                        {selectedPatient360.risk_scores?.risk_level}
                      </span>
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-gray-500">Risk Factors</p>
                    <div className="flex flex-wrap gap-1 justify-end mt-1">
                      {selectedPatient360.risk_scores?.risk_factors?.map((f, i) => (
                        <span key={i} className="text-xs bg-white px-2 py-1 rounded">{f}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Conditions & Medications */}
              <div className="grid md:grid-cols-2 gap-4">
                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 flex items-center gap-2 mb-3">
                    <Activity className="w-4 h-4 text-red-500" /> Active Conditions
                  </h3>
                  <div className="space-y-2">
                    {selectedPatient360.conditions?.map((c) => (
                      <div key={c.id} className="flex justify-between items-center py-2 border-b last:border-0">
                        <div>
                          <p className="font-medium text-sm">{c.display}</p>
                          <p className="text-xs text-gray-500">{c.code}</p>
                        </div>
                        <span className={`text-xs px-2 py-1 rounded ${c.status === 'active' ? 'bg-red-100 text-red-700' : 'bg-gray-100'}`}>
                          {c.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="border rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 flex items-center gap-2 mb-3">
                    <Pill className="w-4 h-4 text-blue-500" /> Medications
                  </h3>
                  <div className="space-y-2">
                    {selectedPatient360.medications?.map((m) => (
                      <div key={m.id} className="flex justify-between items-center py-2 border-b last:border-0">
                        <div>
                          <p className="font-medium text-sm">{m.display}</p>
                          <p className="text-xs text-gray-500">{m.dosage} - {m.frequency}</p>
                        </div>
                        <span className={`text-xs px-2 py-1 rounded ${m.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100'}`}>
                          {m.status}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Financial Summary */}
              <div className="border rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2 mb-3">
                  <DollarSign className="w-4 h-4 text-green-500" /> Financial Summary
                </h3>
                <div className="grid grid-cols-4 gap-4">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-gray-900">${selectedPatient360.financial_summary?.total_billed?.toLocaleString()}</p>
                    <p className="text-xs text-gray-500">Total Billed</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-green-600">${selectedPatient360.financial_summary?.total_paid?.toLocaleString()}</p>
                    <p className="text-xs text-gray-500">Total Paid</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-red-600">${selectedPatient360.financial_summary?.total_denied?.toLocaleString()}</p>
                    <p className="text-xs text-gray-500">Total Denied</p>
                  </div>
                  <div className="text-center">
                    <p className="text-2xl font-bold text-blue-600">{Math.round(parseFloat(selectedPatient360.financial_summary?.collection_rate || '0') * 100)}%</p>
                    <p className="text-xs text-gray-500">Collection Rate</p>
                  </div>
                </div>
              </div>

              {/* Recent Encounters */}
              <div className="border rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2 mb-3">
                  <FileText className="w-4 h-4 text-purple-500" /> Recent Encounters
                </h3>
                <div className="space-y-2">
                  {selectedPatient360.encounters?.slice(0, 5).map((e) => (
                    <div key={e.id} className="flex justify-between items-center py-2 border-b last:border-0">
                      <div>
                        <p className="font-medium text-sm capitalize">{e.type}</p>
                        <p className="text-xs text-gray-500">{new Date(e.admit_date).toLocaleDateString()}</p>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded ${e.status === 'finished' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                        {e.status}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Loading overlay for 360 */}
      {loading360 && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-8 flex flex-col items-center gap-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="text-gray-600">Loading Patient 360 View...</p>
          </div>
        </div>
      )}
    </div>
  )
}
