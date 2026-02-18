'use client'

import { useState, useEffect } from 'react'
import { Bot, Brain, Database, Activity, AlertTriangle, Send, Loader2, CheckCircle, XCircle, Clock, Zap, FileText, TrendingUp, Users, Shield } from 'lucide-react'

const API_BASE = 'http://localhost:8001'

interface AgentActivity {
  timestamp: string
  agent: string
  action: string
  data_sources: string[]
  input_summary?: string
  output_summary?: string
}

interface OrchestratorResponse {
  answer: string
  task_type: string | null
  activities: AgentActivity[]
  insights: string[]
  confidence: number
  data_sources_used: string[]
}

interface TriageResponse {
  report: string
  alerts: Array<{
    type: string
    priority: string
    patient_id: string
    patient_name: string
    mrn: string
    description: string
  }>
  priority_counts: {
    critical?: number
    high?: number
    medium?: number
    low?: number
  }
  recommendations: string[]
  generated_at: string | null
}

interface DataMoatInfo {
  description: string
  data_sources: Array<{ name: string; type: string; data: string }>
  tools: Record<string, { description: string; parameters: Record<string, string> }>
}

const priorityColors = {
  critical: 'bg-red-100 text-red-700 border-red-300',
  high: 'bg-orange-100 text-orange-700 border-orange-300',
  medium: 'bg-yellow-100 text-yellow-700 border-yellow-300',
  low: 'bg-green-100 text-green-700 border-green-300',
}

const agentColors = {
  orchestrator: 'bg-purple-100 text-purple-700',
  action_agent: 'bg-blue-100 text-blue-700',
  triage_agent: 'bg-red-100 text-red-700',
  insight_agent: 'bg-green-100 text-green-700',
}

export default function AgentsPage() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [orchestratorResult, setOrchestratorResult] = useState<OrchestratorResponse | null>(null)
  const [triageResult, setTriageResult] = useState<TriageResponse | null>(null)
  const [dataMoatInfo, setDataMoatInfo] = useState<DataMoatInfo | null>(null)
  const [activeTab, setActiveTab] = useState<'orchestrator' | 'triage' | 'data-moat'>('orchestrator')
  const [agentStatus, setAgentStatus] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)
  const [statusLoading, setStatusLoading] = useState(true)

  useEffect(() => {
    fetchAgentStatus()
    fetchDataMoatInfo()
  }, [])

  const fetchAgentStatus = async () => {
    setStatusLoading(true)
    try {
      const res = await fetch(`${API_BASE}/v1/agents/status`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setAgentStatus(data)
      setError(null)
    } catch (err: any) {
      console.error('Failed to fetch agent status:', err)
      setError(`Cannot connect to API at ${API_BASE}. Make sure the backend is running.`)
    } finally {
      setStatusLoading(false)
    }
  }

  const fetchDataMoatInfo = async () => {
    try {
      const res = await fetch(`${API_BASE}/v1/agents/data-moat/tools`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setDataMoatInfo(data)
    } catch (err: any) {
      console.error('Failed to fetch data moat info:', err)
    }
  }

  const runOrchestrator = async () => {
    if (!query.trim()) return
    setLoading(true)
    setOrchestratorResult(null)
    setError(null)

    try {
      const res = await fetch(`${API_BASE}/v1/agents/orchestrate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query })
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      const data = await res.json()
      setOrchestratorResult(data)
    } catch (err: any) {
      console.error('Orchestrator failed:', err)
      setError(`Orchestrator request failed: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const runTriage = async () => {
    setLoading(true)
    setTriageResult(null)
    setError(null)

    try {
      const res = await fetch(`${API_BASE}/v1/agents/triage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`)
      const data = await res.json()
      setTriageResult(data)
    } catch (err: any) {
      console.error('Triage failed:', err)
      setError(`Triage request failed: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const exampleQueries = [
    { label: 'Review Patient', query: 'Review patient-001', icon: Users },
    { label: 'Denial Analysis', query: 'Analyze denial backlog', icon: FileText },
    { label: 'High Risk Patients', query: 'Find high risk patients', icon: AlertTriangle },
    { label: 'Revenue Impact', query: 'Revenue impact analysis', icon: TrendingUp },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Brain className="w-7 h-7 text-purple-600" />
            VeritOS AI Agents
          </h1>
          <p className="text-gray-500 mt-1">
            LangGraph-powered agents orchestrating across the Data Moat
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-xs font-medium ${agentStatus?.llm_provider === 'mock' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'}`}>
            LLM: {agentStatus?.model || 'mock'}
          </span>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-3">
          <XCircle className="w-5 h-5" />
          <div>
            <p className="font-medium">Connection Error</p>
            <p className="text-sm">{error}</p>
          </div>
          <button onClick={fetchAgentStatus} className="ml-auto px-3 py-1 bg-red-100 hover:bg-red-200 rounded text-sm">
            Retry
          </button>
        </div>
      )}

      {/* Loading State */}
      {statusLoading && !agentStatus && (
          <div className="bg-white rounded-lg shadow p-6 flex items-center justify-center gap-3">
          <Loader2 className="w-6 h-6 animate-spin text-purple-600" />
          <span className="text-gray-600">Connecting to VeritOS API...</span>
        </div>
      )}

      {/* Agent Status Cards */}
      {agentStatus?.agents && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          {Object.entries(agentStatus.agents).map(([name, info]: [string, any]) => (
            <div key={name} className="bg-white rounded-lg shadow p-3 border-l-4 border-purple-500">
              <div className="flex items-center gap-2">
                <Bot className="w-5 h-5 text-purple-600" />
                <span className="font-medium text-sm capitalize">{name.replace('_', ' ')}</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">{info.description}</p>
            </div>
          ))}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b">
        <button
          onClick={() => setActiveTab('orchestrator')}
          className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'orchestrator' ? 'border-purple-600 text-purple-600' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Brain className="w-4 h-4 inline mr-2" />
          Orchestrator
        </button>
        <button
          onClick={() => setActiveTab('triage')}
          className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'triage' ? 'border-red-600 text-red-600' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Activity className="w-4 h-4 inline mr-2" />
          Clinical Triage
        </button>
        <button
          onClick={() => setActiveTab('data-moat')}
          className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${
            activeTab === 'data-moat' ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <Database className="w-4 h-4 inline mr-2" />
          Data Moat
        </button>
      </div>

      {/* Orchestrator Tab */}
      {activeTab === 'orchestrator' && (
        <div className="space-y-4">
          {/* Query Input */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold text-gray-900 mb-3">Ask the Orchestrator</h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && runOrchestrator()}
                placeholder="e.g., Review patient-001, Analyze denial backlog, Find high risk patients..."
                className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/20"
              />
              <button
                onClick={runOrchestrator}
                disabled={loading || !query.trim()}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Run
              </button>
            </div>
            
            {/* Example Queries */}
            <div className="flex gap-2 mt-3">
              {exampleQueries.map((ex) => (
                <button
                  key={ex.query}
                  onClick={() => setQuery(ex.query)}
                  className="px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 flex items-center gap-1"
                >
                  <ex.icon className="w-3 h-3" />
                  {ex.label}
                </button>
              ))}
            </div>
          </div>

          {/* Results */}
          {orchestratorResult && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* Main Answer */}
              <div className="lg:col-span-2 bg-white rounded-lg shadow p-4">
                <div className="flex justify-between items-start mb-3">
                  <h3 className="font-semibold text-gray-900">Analysis Result</h3>
                  <div className="flex items-center gap-2">
                    {orchestratorResult.task_type && (
                      <span className="px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded">
                        {orchestratorResult.task_type}
                      </span>
                    )}
                    <span className="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">
                      {Math.round(orchestratorResult.confidence * 100)}% confidence
                    </span>
                  </div>
                </div>
                <div className="prose prose-sm max-w-none">
                  <pre className="whitespace-pre-wrap text-sm text-gray-700 bg-gray-50 p-4 rounded-lg">
                    {orchestratorResult.answer}
                  </pre>
                </div>
                
                {/* Data Sources */}
                {orchestratorResult.data_sources_used.length > 0 && (
                  <div className="mt-4 pt-4 border-t">
                    <p className="text-xs text-gray-500 mb-2">Data Sources Accessed:</p>
                    <div className="flex gap-2">
                      {orchestratorResult.data_sources_used.map((source) => (
                        <span key={source} className="px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded flex items-center gap-1">
                          <Database className="w-3 h-3" />
                          {source}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Agent Activity Timeline */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-yellow-500" />
                  Agent Activity
                </h3>
                <div className="space-y-3">
                  {orchestratorResult.activities.map((activity, i) => (
                    <div key={i} className="relative pl-4 border-l-2 border-purple-200">
                      <div className="absolute -left-1.5 top-0 w-3 h-3 rounded-full bg-purple-500"></div>
                      <div className={`px-2 py-1 rounded text-xs inline-block mb-1 ${agentColors[activity.agent as keyof typeof agentColors] || 'bg-gray-100 text-gray-700'}`}>
                        {activity.agent}
                      </div>
                      <p className="text-sm font-medium text-gray-900">{activity.action}</p>
                      {activity.output_summary && (
                        <p className="text-xs text-gray-500 mt-1">{activity.output_summary}</p>
                      )}
                      {activity.data_sources.length > 0 && (
                        <div className="flex gap-1 mt-1">
                          {activity.data_sources.map((ds) => (
                            <span key={ds} className="text-xs text-blue-600">{ds}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Triage Tab */}
      {activeTab === 'triage' && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="font-semibold text-gray-900">Clinical Triage Scan</h3>
                <p className="text-sm text-gray-500">Scan the Data Moat for patients needing clinical attention</p>
              </div>
              <button
                onClick={runTriage}
                disabled={loading}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
                Run Triage
              </button>
            </div>
          </div>

          {triageResult && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* Alert Summary */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Alert Summary</h3>
                <div className="space-y-2">
                  <div className="flex justify-between items-center p-2 bg-red-50 rounded">
                    <span className="text-sm text-red-700">Critical</span>
                    <span className="text-2xl font-bold text-red-700">{triageResult.priority_counts.critical || 0}</span>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-orange-50 rounded">
                    <span className="text-sm text-orange-700">High</span>
                    <span className="text-2xl font-bold text-orange-700">{triageResult.priority_counts.high || 0}</span>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-yellow-50 rounded">
                    <span className="text-sm text-yellow-700">Medium</span>
                    <span className="text-2xl font-bold text-yellow-700">{triageResult.priority_counts.medium || 0}</span>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-green-50 rounded">
                    <span className="text-sm text-green-700">Low</span>
                    <span className="text-2xl font-bold text-green-700">{triageResult.priority_counts.low || 0}</span>
                  </div>
                </div>
              </div>

              {/* Recommendations */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Recommendations</h3>
                <div className="space-y-2">
                  {triageResult.recommendations.map((rec, i) => (
                    <div key={i} className="p-2 bg-gray-50 rounded text-sm text-gray-700">
                      {rec}
                    </div>
                  ))}
                </div>
              </div>

              {/* Alert List */}
              <div className="bg-white rounded-lg shadow p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Patient Alerts</h3>
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {triageResult.alerts.slice(0, 10).map((alert, i) => (
                    <div key={i} className={`p-2 rounded border ${priorityColors[alert.priority as keyof typeof priorityColors] || 'bg-gray-100'}`}>
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-medium text-sm">{alert.patient_name}</p>
                          <p className="text-xs opacity-75">{alert.mrn}</p>
                        </div>
                        <span className="text-xs font-medium uppercase">{alert.priority}</span>
                      </div>
                      <p className="text-xs mt-1">{alert.description}</p>
                    </div>
                  ))}
                  {triageResult.alerts.length === 0 && (
                    <p className="text-sm text-gray-500 text-center py-4">No alerts at this time</p>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Data Moat Tab */}
      {activeTab === 'data-moat' && dataMoatInfo && (
        <div className="space-y-4">
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg shadow p-6 text-white">
            <h3 className="text-xl font-bold flex items-center gap-2">
              <Shield className="w-6 h-6" />
              The VeritOS Data Moat
            </h3>
            <p className="mt-2 opacity-90">{dataMoatInfo.description}</p>
          </div>

          {/* Data Sources */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {dataMoatInfo.data_sources.map((source) => (
              <div key={source.name} className="bg-white rounded-lg shadow p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Database className="w-5 h-5 text-blue-600" />
                  <h4 className="font-semibold text-gray-900">{source.name}</h4>
                </div>
                <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">{source.type}</span>
                <p className="text-sm text-gray-600 mt-2">{source.data}</p>
              </div>
            ))}
          </div>

          {/* Available Tools */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold text-gray-900 mb-4">Agent Tools (Data Moat Access)</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(dataMoatInfo.tools).map(([name, tool]) => (
                <div key={name} className="p-4 bg-gray-50 rounded-lg">
                  <h4 className="font-mono text-sm font-semibold text-purple-600">{name}()</h4>
                  <p className="text-sm text-gray-600 mt-1">{tool.description}</p>
                  {Object.keys(tool.parameters).length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs text-gray-500">Parameters:</p>
                      <div className="flex gap-2 mt-1">
                        {Object.entries(tool.parameters).map(([param, type]) => (
                          <span key={param} className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                            {param}: {type}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
