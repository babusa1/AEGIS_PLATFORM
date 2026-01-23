'use client'

import { useState } from 'react'
import { Search, Filter, UserCircle, Eye, Bot } from 'lucide-react'

const patients = [
  { id: 'P001', mrn: 'MRN-78234', name: 'John Smith', dob: '1965-03-15', gender: 'Male', payer: 'Blue Cross', riskLevel: 'high', encounters: 12, lastVisit: '2024-01-15' },
  { id: 'P002', mrn: 'MRN-78235', name: 'Maria Garcia', dob: '1978-07-22', gender: 'Female', payer: 'Aetna', riskLevel: 'medium', encounters: 5, lastVisit: '2024-01-12' },
  { id: 'P003', mrn: 'MRN-78236', name: 'Robert Johnson', dob: '1952-11-08', gender: 'Male', payer: 'Medicare', riskLevel: 'high', encounters: 18, lastVisit: '2024-01-18' },
  { id: 'P004', mrn: 'MRN-78237', name: 'Emily Davis', dob: '1990-04-30', gender: 'Female', payer: 'United', riskLevel: 'low', encounters: 3, lastVisit: '2024-01-05' },
  { id: 'P005', mrn: 'MRN-78238', name: 'Michael Wilson', dob: '1970-09-12', gender: 'Male', payer: 'Cigna', riskLevel: 'medium', encounters: 8, lastVisit: '2024-01-10' },
  { id: 'P006', mrn: 'MRN-78239', name: 'Sarah Brown', dob: '1985-01-25', gender: 'Female', payer: 'Blue Cross', riskLevel: 'low', encounters: 4, lastVisit: '2024-01-08' },
]

const riskColors = {
  high: 'bg-red-100 text-red-700',
  medium: 'bg-yellow-100 text-yellow-700',
  low: 'bg-green-100 text-green-700',
}

export default function PatientsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedPatient, setSelectedPatient] = useState<string | null>(null)

  const filteredPatients = patients.filter(p => 
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.mrn.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Patients</h1>
          <p className="text-gray-500 mt-1">Manage and view patient information</p>
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
            className="w-full pl-10 pr-4 py-2 bg-white border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-aegis-primary/20"
          />
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50">
          <Filter className="w-4 h-4" />
          Filters
        </button>
      </div>

      {/* Patient Table */}
      <div className="card overflow-hidden p-0">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Patient</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">MRN</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">DOB</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Payer</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Risk</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Encounters</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Last Visit</th>
              <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {filteredPatients.map((patient) => (
              <tr key={patient.id} className="hover:bg-gray-50 transition-colors">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-aegis-primary/10 rounded-full flex items-center justify-center">
                      <UserCircle className="w-6 h-6 text-aegis-primary" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900">{patient.name}</p>
                      <p className="text-sm text-gray-500">{patient.gender}</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600 font-mono">{patient.mrn}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{patient.dob}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{patient.payer}</td>
                <td className="px-6 py-4">
                  <span className={`badge ${riskColors[patient.riskLevel as keyof typeof riskColors]}`}>
                    {patient.riskLevel}
                  </span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-600">{patient.encounters}</td>
                <td className="px-6 py-4 text-sm text-gray-600">{patient.lastVisit}</td>
                <td className="px-6 py-4 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button className="p-2 text-gray-500 hover:text-aegis-primary hover:bg-aegis-primary/10 rounded-lg transition-colors">
                      <Eye className="w-4 h-4" />
                    </button>
                    <button 
                      className="p-2 text-gray-500 hover:text-aegis-primary hover:bg-aegis-primary/10 rounded-lg transition-colors"
                      title="Generate 360 View"
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
    </div>
  )
}
