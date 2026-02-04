'use client'

import { useState, useEffect } from 'react'
import { Play, GitBranch, Database, Loader2, CheckCircle, Clock, AlertCircle, ChevronRight, ExternalLink, Workflow, Zap, Brain, FileText, Activity, Users } from 'lucide-react'

const API_BASE = 'http://localhost:8001'

interface WorkflowStep {
  node: string
  timestamp: string
  input_data: Record<string, any> | null
  output_data: Record<string, any> | null
  duration_ms: number
  status: string
}

interface WorkflowResult {
  success: boolean
  execution_id: string
  workflow_id: string
  result: any
  error: string | null
  trace: WorkflowStep[]
  workflow: any
  execution_time_ms: number
}

interface WorkflowDefinition {
  name: string
  framework: string
  nodes: Array<{ id: string; label: string; type: string }>
  edges: Array<{ from: string; to: string; label?: string }>
  mermaid: string
  data_moat_connections: Array<{ agent: string; sources: string[] }>
}

const nodeColors: Record<string, string> = {
  entry: 'bg-green-500',
  router: 'bg-purple-500',
  agent: 'bg-blue-500',
  processor: 'bg-orange-500',
  exit: 'bg-red-500',
}

const nodeIcons: Record<string, any> = {
  supervisor: Brain,
  patient_agent: Users,
  denial_agent: FileText,
  triage_agent: Activity,
  synthesizer: Zap,
}

export default function WorkflowsPage() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<WorkflowResult | null>(null)
  const [definition, setDefinition] = useState<WorkflowDefinition | null>(null)
  const [activeStep, setActiveStep] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchWorkflowDefinition()
  }, [])

  const fetchWorkflowDefinition = async () => {
    try {
      const res = await fetch(`${API_BASE}/v1/workflows/definition/healthcare_orchestrator`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setDefinition(data)
    } catch (err: any) {
      setError(`Cannot connect to API: ${err.message}`)
    }
  }

  const runWorkflow = async () => {
    if (!query.trim()) return
    setLoading(true)
    setResult(null)
    setError(null)
    setActiveStep(null)

    try {
      const res = await fetch(`${API_BASE}/v1/workflows/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, workflow_id: 'healthcare_orchestrator' })
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setResult(data)
    } catch (err: any) {
      setError(`Workflow failed: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const exampleQueries = [
    { text: 'Review patient-003', intent: 'Patient Analysis' },
    { text: 'Analyze denial backlog', intent: 'Denial Management' },
    { text: 'Show clinical alerts', intent: 'Clinical Triage' },
    { text: 'High risk patients summary', intent: 'Triage' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Workflow className="w-7 h-7 text-purple-600" />
            LangGraph Workflows
          </h1>
          <p className="text-gray-500 mt-1">
            Multi-agent orchestration with visual execution traces
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full text-xs font-medium bg-purple-100 text-purple-700">
            Framework: LangGraph
          </span>
          <a 
            href="https://langchain-ai.github.io/langgraph/" 
            target="_blank"
            className="px-3 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700 hover:bg-gray-200 flex items-center gap-1"
          >
            Docs <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Workflow Graph */}
        <div className="bg-white rounded-lg shadow p-4">
          <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
            <GitBranch className="w-5 h-5 text-purple-600" />
            Workflow Graph
          </h3>
          
          {definition && (
            <div className="space-y-4">
              {/* Visual Graph */}
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="flex flex-col items-center gap-2">
                  {/* START */}
                  <div className={`px-4 py-2 rounded-full text-white text-sm font-medium ${nodeColors.entry} ${result?.trace.some(s => s.node === 'start') ? 'ring-4 ring-green-300' : ''}`}>
                    START
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-400 rotate-90" />
                  
                  {/* SUPERVISOR */}
                  <div className={`px-4 py-3 rounded-lg text-white text-sm font-medium ${nodeColors.router} ${result?.trace.some(s => s.node === 'supervisor') ? 'ring-4 ring-purple-300' : ''}`}>
                    <Brain className="w-4 h-4 inline mr-2" />
                    Supervisor (Router)
                  </div>
                  
                  {/* Branch to agents */}
                  <div className="flex items-center gap-2 text-gray-400">
                    <div className="w-20 h-0.5 bg-gray-300"></div>
                    <span className="text-xs">routes to</span>
                    <div className="w-20 h-0.5 bg-gray-300"></div>
                  </div>
                  
                  {/* Agent Row */}
                  <div className="flex gap-3">
                    <div className={`px-3 py-2 rounded-lg text-white text-xs font-medium ${nodeColors.agent} ${result?.trace.some(s => s.node === 'patient_agent') ? 'ring-4 ring-blue-300' : ''}`}>
                      <Users className="w-3 h-3 inline mr-1" />
                      Patient
                    </div>
                    <div className={`px-3 py-2 rounded-lg text-white text-xs font-medium ${nodeColors.agent} ${result?.trace.some(s => s.node === 'denial_agent') ? 'ring-4 ring-blue-300' : ''}`}>
                      <FileText className="w-3 h-3 inline mr-1" />
                      Denial
                    </div>
                    <div className={`px-3 py-2 rounded-lg text-white text-xs font-medium ${nodeColors.agent} ${result?.trace.some(s => s.node === 'triage_agent') ? 'ring-4 ring-blue-300' : ''}`}>
                      <Activity className="w-3 h-3 inline mr-1" />
                      Triage
                    </div>
                  </div>
                  
                  <ChevronRight className="w-4 h-4 text-gray-400 rotate-90" />
                  
                  {/* SYNTHESIZER */}
                  <div className={`px-4 py-3 rounded-lg text-white text-sm font-medium ${nodeColors.processor} ${result?.trace.some(s => s.node === 'synthesizer') ? 'ring-4 ring-orange-300' : ''}`}>
                    <Zap className="w-4 h-4 inline mr-2" />
                    Synthesizer
                  </div>
                  
                  <ChevronRight className="w-4 h-4 text-gray-400 rotate-90" />
                  
                  {/* END */}
                  <div className={`px-4 py-2 rounded-full text-white text-sm font-medium ${nodeColors.exit}`}>
                    END
                  </div>
                </div>
              </div>

              {/* Data Moat Connections */}
              <div className="border-t pt-4">
                <p className="text-xs text-gray-500 mb-2 font-medium">Data Moat Connections:</p>
                <div className="grid grid-cols-2 gap-2">
                  {definition.data_moat_connections.map((conn) => (
                    <div key={conn.agent} className="flex items-center gap-2 text-xs">
                      <span className="font-medium text-gray-700">{conn.agent.replace('_', ' ')}:</span>
                      <div className="flex gap-1">
                        {conn.sources.map((src) => (
                          <span key={src} className="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded">
                            {src}
                          </span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Mermaid Code */}
              <details className="border-t pt-4">
                <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">
                  View Mermaid Diagram Code
                </summary>
                <pre className="mt-2 text-xs bg-gray-900 text-green-400 p-3 rounded overflow-x-auto">
                  {definition.mermaid}
                </pre>
              </details>
            </div>
          )}
        </div>

        {/* Right: Run & Results */}
        <div className="space-y-4">
          {/* Query Input */}
          <div className="bg-white rounded-lg shadow p-4">
            <h3 className="font-semibold text-gray-900 mb-3">Run Workflow</h3>
            <div className="flex gap-2">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && runWorkflow()}
                placeholder="Enter your query..."
                className="flex-1 px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500/20"
              />
              <button
                onClick={runWorkflow}
                disabled={loading || !query.trim()}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                Run
              </button>
            </div>
            
            {/* Example Queries */}
            <div className="flex flex-wrap gap-2 mt-3">
              {exampleQueries.map((ex) => (
                <button
                  key={ex.text}
                  onClick={() => setQuery(ex.text)}
                  className="px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200"
                >
                  {ex.text}
                </button>
              ))}
            </div>
          </div>

          {/* Execution Trace */}
          {result && (
            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex justify-between items-center mb-3">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                  <Clock className="w-4 h-4 text-gray-500" />
                  Execution Trace
                </h3>
                <span className="text-xs text-gray-500">
                  {result.execution_time_ms}ms total
                </span>
              </div>
              
              <div className="space-y-2">
                {result.trace.map((step, i) => {
                  const Icon = nodeIcons[step.node] || CheckCircle
                  return (
                    <div 
                      key={i}
                      onClick={() => setActiveStep(activeStep === i ? null : i)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        activeStep === i ? 'border-purple-500 bg-purple-50' : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Icon className={`w-4 h-4 ${step.status === 'completed' ? 'text-green-500' : 'text-gray-400'}`} />
                          <span className="font-medium text-sm">{step.node}</span>
                        </div>
                        <span className="text-xs text-gray-500">{step.duration_ms}ms</span>
                      </div>
                      
                      {activeStep === i && step.output_data && (
                        <div className="mt-2 pt-2 border-t text-xs">
                          <p className="text-gray-500 mb-1">Output:</p>
                          <pre className="bg-gray-100 p-2 rounded overflow-x-auto">
                            {JSON.stringify(step.output_data, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Result */}
          {result?.result && (
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                {result.success ? (
                  <CheckCircle className="w-4 h-4 text-green-500" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-red-500" />
                )}
                Result
              </h3>
              
              {result.result.summary && (
                <div className="bg-gray-50 rounded-lg p-3">
                  <pre className="whitespace-pre-wrap text-sm text-gray-700">
                    {result.result.summary}
                  </pre>
                </div>
              )}
              
              {result.result.data_sources && result.result.data_sources.length > 0 && (
                <div className="mt-3 pt-3 border-t flex items-center gap-2">
                  <Database className="w-4 h-4 text-blue-500" />
                  <span className="text-xs text-gray-500">Data Sources:</span>
                  {result.result.data_sources.map((src: string) => (
                    <span key={src} className="px-2 py-0.5 text-xs bg-blue-100 text-blue-700 rounded">
                      {src}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* n8n Integration Info */}
      <div className="bg-gradient-to-r from-orange-50 to-yellow-50 rounded-lg shadow p-4 border border-orange-200">
        <h3 className="font-semibold text-gray-900 mb-2 flex items-center gap-2">
          <ExternalLink className="w-5 h-5 text-orange-600" />
          n8n Integration
        </h3>
        <p className="text-sm text-gray-600 mb-3">
          This workflow is n8n-compatible. Use the HTTP Request node with:
        </p>
        <div className="bg-white rounded p-3 font-mono text-xs">
          <p><span className="text-purple-600">POST</span> {API_BASE}/v1/workflows/webhook</p>
          <p className="mt-2 text-gray-500">Body:</p>
          <pre className="text-gray-700">{`{
  "query": "Your natural language query",
  "workflow_id": "healthcare_orchestrator"
}`}</pre>
        </div>
      </div>
    </div>
  )
}
