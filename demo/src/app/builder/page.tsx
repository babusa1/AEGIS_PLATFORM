'use client'

import { useState, useEffect, useCallback } from 'react'
import { 
  Play, Save, Plus, Trash2, Settings, Database, Brain, Users, FileText, 
  Activity, Zap, Bell, Globe, Filter, Calculator, GitBranch, Loader2,
  ChevronRight, CheckCircle, AlertCircle, GripVertical, X
} from 'lucide-react'

const API_BASE = 'http://localhost:8001'

interface ToolDefinition {
  id: string
  name: string
  description: string
  category: string
  icon: string
  color: string
  inputs: Array<{ name: string; type: string; required?: boolean }>
  outputs: Array<{ name: string; type: string }>
}

interface WorkflowNode {
  id: string
  type: string
  name: string
  description?: string
  config: Record<string, any>
  position_x: number
  position_y: number
}

interface WorkflowEdge {
  id: string
  source: string
  target: string
  label?: string
}

const iconMap: Record<string, any> = {
  users: Users,
  'file-x': FileText,
  'heart-pulse': Activity,
  flask: Database,
  'file-text': FileText,
  'user-check': Users,
  'file-search': FileText,
  activity: Activity,
  brain: Brain,
  tags: Database,
  'file-pen': FileText,
  bell: Bell,
  globe: Globe,
  filter: Filter,
  calculator: Calculator,
  tool: Settings,
}

const nodeTypeColors: Record<string, string> = {
  start: 'bg-green-500',
  end: 'bg-red-500',
  router: 'bg-purple-500',
  query_patients: 'bg-blue-500',
  query_denials: 'bg-red-400',
  query_vitals: 'bg-emerald-500',
  query_labs: 'bg-violet-500',
  query_claims: 'bg-amber-500',
  patient_agent: 'bg-cyan-500',
  denial_agent: 'bg-pink-500',
  triage_agent: 'bg-rose-500',
  llm_generate: 'bg-purple-600',
  generate_appeal: 'bg-green-600',
  send_alert: 'bg-yellow-500',
  call_api: 'bg-slate-500',
}

export default function WorkflowBuilder() {
  const [tools, setTools] = useState<Record<string, ToolDefinition[]>>({})
  const [nodes, setNodes] = useState<WorkflowNode[]>([
    { id: 'start', type: 'start', name: 'Start', config: {}, position_x: 50, position_y: 50 },
    { id: 'end', type: 'end', name: 'End', config: {}, position_x: 50, position_y: 400 },
  ])
  const [edges, setEdges] = useState<WorkflowEdge[]>([])
  const [selectedNode, setSelectedNode] = useState<string | null>(null)
  const [workflowName, setWorkflowName] = useState('New Workflow')
  const [loading, setLoading] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [executionResult, setExecutionResult] = useState<any>(null)
  const [showToolPalette, setShowToolPalette] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchTools()
  }, [])

  const fetchTools = async () => {
    try {
      const res = await fetch(`${API_BASE}/v1/orchestrator/tools`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setTools(data.tools || {})
    } catch (err: any) {
      setError(`Cannot connect to API: ${err.message}`)
    }
  }

  const addNode = (tool: ToolDefinition) => {
    const newNode: WorkflowNode = {
      id: `node-${Date.now()}`,
      type: tool.id,
      name: tool.name,
      description: tool.description,
      config: {},
      position_x: 50,
      position_y: (nodes.length - 1) * 100 + 50,
    }
    
    // Insert before end node
    const newNodes = [...nodes]
    const endIndex = newNodes.findIndex(n => n.type === 'end')
    if (endIndex > -1) {
      newNodes.splice(endIndex, 0, newNode)
    } else {
      newNodes.push(newNode)
    }
    setNodes(newNodes)
    setSelectedNode(newNode.id)
    
    // Auto-connect to previous node
    if (newNodes.length >= 3) {
      const prevNode = newNodes[newNodes.length - 3]
      if (prevNode && prevNode.type !== 'end') {
        const newEdge: WorkflowEdge = {
          id: `edge-${Date.now()}`,
          source: prevNode.id,
          target: newNode.id,
        }
        setEdges([...edges, newEdge])
      }
    }
  }

  const removeNode = (nodeId: string) => {
    if (nodeId === 'start' || nodeId === 'end') return
    setNodes(nodes.filter(n => n.id !== nodeId))
    setEdges(edges.filter(e => e.source !== nodeId && e.target !== nodeId))
    if (selectedNode === nodeId) setSelectedNode(null)
  }

  const connectNodes = (sourceId: string, targetId: string) => {
    // Check if edge already exists
    if (edges.some(e => e.source === sourceId && e.target === targetId)) return
    
    const newEdge: WorkflowEdge = {
      id: `edge-${Date.now()}`,
      source: sourceId,
      target: targetId,
    }
    setEdges([...edges, newEdge])
  }

  const autoConnect = () => {
    // Simple auto-connect: chain all nodes in order
    const newEdges: WorkflowEdge[] = []
    for (let i = 0; i < nodes.length - 1; i++) {
      newEdges.push({
        id: `edge-${i}`,
        source: nodes[i].id,
        target: nodes[i + 1].id,
      })
    }
    setEdges(newEdges)
  }

  const saveWorkflow = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/v1/orchestrator/workflows`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: workflowName,
          description: `Created with visual builder`,
          nodes,
          edges,
          tags: ['custom'],
        })
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      alert(`Workflow saved! ID: ${data.id}`)
    } catch (err: any) {
      setError(`Save failed: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const executeWorkflow = async () => {
    setExecuting(true)
    setExecutionResult(null)
    
    // For demo, use quick execution
    try {
      const res = await fetch(`${API_BASE}/v1/orchestrator/execute-quick?query=Get%20patient%20summary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setExecutionResult(data)
    } catch (err: any) {
      setError(`Execution failed: ${err.message}`)
    } finally {
      setExecuting(false)
    }
  }

  const loadTemplate = (templateId: string) => {
    if (templateId === 'patient-risk') {
      setWorkflowName('Patient Risk Assessment')
      setNodes([
        { id: 'start', type: 'start', name: 'Start', config: {}, position_x: 50, position_y: 50 },
        { id: 'query', type: 'query_patients', name: 'Get Patient Data', config: {}, position_x: 50, position_y: 150 },
        { id: 'analyze', type: 'patient_agent', name: 'Analyze Risk', config: {}, position_x: 50, position_y: 250 },
        { id: 'alert', type: 'send_alert', name: 'Send Alert', config: {}, position_x: 50, position_y: 350 },
        { id: 'end', type: 'end', name: 'End', config: {}, position_x: 50, position_y: 450 },
      ])
      autoConnect()
    } else if (templateId === 'denial-appeal') {
      setWorkflowName('Denial Appeal Workflow')
      setNodes([
        { id: 'start', type: 'start', name: 'Start', config: {}, position_x: 50, position_y: 50 },
        { id: 'denial', type: 'query_denials', name: 'Get Denial', config: {}, position_x: 50, position_y: 150 },
        { id: 'patient', type: 'query_patients', name: 'Get Patient Data', config: {}, position_x: 50, position_y: 250 },
        { id: 'analyze', type: 'denial_agent', name: 'Analyze Denial', config: {}, position_x: 50, position_y: 350 },
        { id: 'appeal', type: 'generate_appeal', name: 'Generate Appeal', config: {}, position_x: 50, position_y: 450 },
        { id: 'end', type: 'end', name: 'End', config: {}, position_x: 50, position_y: 550 },
      ])
    } else if (templateId === 'triage') {
      setWorkflowName('Clinical Triage')
      setNodes([
        { id: 'start', type: 'start', name: 'Start', config: {}, position_x: 50, position_y: 50 },
        { id: 'vitals', type: 'query_vitals', name: 'Scan Vitals', config: {}, position_x: 50, position_y: 150 },
        { id: 'labs', type: 'query_labs', name: 'Scan Labs', config: {}, position_x: 50, position_y: 250 },
        { id: 'triage', type: 'triage_agent', name: 'Triage Agent', config: {}, position_x: 50, position_y: 350 },
        { id: 'alert', type: 'send_alert', name: 'Send Alerts', config: {}, position_x: 50, position_y: 450 },
        { id: 'end', type: 'end', name: 'End', config: {}, position_x: 50, position_y: 550 },
      ])
    }
    setTimeout(autoConnect, 100)
  }

  useEffect(() => {
    autoConnect()
  }, [nodes.length])

  const getNodeIcon = (type: string) => {
    // Find tool definition
    for (const category of Object.values(tools)) {
      const tool = category.find(t => t.id === type)
      if (tool) {
        const Icon = iconMap[tool.icon] || Settings
        return Icon
      }
    }
    if (type === 'start') return Play
    if (type === 'end') return CheckCircle
    return Settings
  }

  return (
    <div className="h-[calc(100vh-120px)] flex gap-4">
      {/* Tool Palette */}
      {showToolPalette && (
        <div className="w-64 bg-white rounded-lg shadow overflow-hidden flex flex-col">
          <div className="p-3 bg-gray-50 border-b flex justify-between items-center">
            <h3 className="font-semibold text-gray-900 text-sm">Tools</h3>
            <button onClick={() => setShowToolPalette(false)} className="text-gray-400 hover:text-gray-600">
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {/* Templates */}
            <div className="mb-4">
              <p className="text-xs font-semibold text-gray-500 mb-2 px-2">TEMPLATES</p>
              <button
                onClick={() => loadTemplate('patient-risk')}
                className="w-full text-left px-3 py-2 text-sm bg-blue-50 text-blue-700 rounded-lg mb-1 hover:bg-blue-100"
              >
                Patient Risk Assessment
              </button>
              <button
                onClick={() => loadTemplate('denial-appeal')}
                className="w-full text-left px-3 py-2 text-sm bg-red-50 text-red-700 rounded-lg mb-1 hover:bg-red-100"
              >
                Denial Appeal
              </button>
              <button
                onClick={() => loadTemplate('triage')}
                className="w-full text-left px-3 py-2 text-sm bg-green-50 text-green-700 rounded-lg mb-1 hover:bg-green-100"
              >
                Clinical Triage
              </button>
            </div>
            
            {/* Tool Categories */}
            {Object.entries(tools).map(([category, categoryTools]) => (
              <div key={category} className="mb-4">
                <p className="text-xs font-semibold text-gray-500 mb-2 px-2">{category.toUpperCase()}</p>
                {categoryTools.map((tool) => {
                  const Icon = iconMap[tool.icon] || Settings
                  return (
                    <button
                      key={tool.id}
                      onClick={() => addNode(tool)}
                      className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
                    >
                      <div className={`w-6 h-6 rounded flex items-center justify-center text-white`} style={{ backgroundColor: tool.color }}>
                        <Icon className="w-3 h-3" />
                      </div>
                      <span className="truncate">{tool.name}</span>
                    </button>
                  )
                })}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Canvas */}
      <div className="flex-1 bg-white rounded-lg shadow overflow-hidden flex flex-col">
        {/* Toolbar */}
        <div className="p-3 bg-gray-50 border-b flex items-center gap-3">
          {!showToolPalette && (
            <button
              onClick={() => setShowToolPalette(true)}
              className="p-2 text-gray-600 hover:bg-gray-200 rounded"
            >
              <Plus className="w-4 h-4" />
            </button>
          )}
          <input
            type="text"
            value={workflowName}
            onChange={(e) => setWorkflowName(e.target.value)}
            className="flex-1 px-3 py-1.5 border border-gray-200 rounded text-sm font-medium"
          />
          <button
            onClick={autoConnect}
            className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-200 rounded flex items-center gap-1"
          >
            <GitBranch className="w-4 h-4" />
            Auto-Connect
          </button>
          <button
            onClick={saveWorkflow}
            disabled={loading}
            className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-1"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
            Save
          </button>
          <button
            onClick={executeWorkflow}
            disabled={executing}
            className="px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 flex items-center gap-1"
          >
            {executing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Run
          </button>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="p-2 bg-red-50 text-red-700 text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
            <button onClick={() => setError(null)} className="ml-auto">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Canvas Area */}
        <div className="flex-1 p-4 overflow-auto bg-gray-50" style={{ backgroundImage: 'radial-gradient(circle, #ddd 1px, transparent 1px)', backgroundSize: '20px 20px' }}>
          <div className="relative min-h-full">
            {/* Nodes */}
            {nodes.map((node, index) => {
              const Icon = getNodeIcon(node.type)
              const isSelected = selectedNode === node.id
              const color = nodeTypeColors[node.type] || 'bg-gray-500'
              
              return (
                <div
                  key={node.id}
                  onClick={() => setSelectedNode(node.id)}
                  className={`absolute flex items-center gap-2 px-4 py-3 bg-white rounded-lg shadow-md border-2 transition-all cursor-pointer ${
                    isSelected ? 'border-blue-500 shadow-lg' : 'border-transparent hover:border-gray-300'
                  }`}
                  style={{ left: node.position_x, top: index * 100 }}
                >
                  <div className={`w-8 h-8 ${color} rounded-lg flex items-center justify-center text-white`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="font-medium text-sm text-gray-900">{node.name}</p>
                    <p className="text-xs text-gray-500">{node.type}</p>
                  </div>
                  {node.type !== 'start' && node.type !== 'end' && (
                    <button
                      onClick={(e) => { e.stopPropagation(); removeNode(node.id); }}
                      className="ml-2 p-1 text-gray-400 hover:text-red-500 rounded"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  )}
                </div>
              )
            })}

            {/* Connection Lines */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ minHeight: nodes.length * 100 + 100 }}>
              {edges.map((edge) => {
                const sourceIndex = nodes.findIndex(n => n.id === edge.source)
                const targetIndex = nodes.findIndex(n => n.id === edge.target)
                if (sourceIndex === -1 || targetIndex === -1) return null
                
                const x1 = 150
                const y1 = sourceIndex * 100 + 30
                const x2 = 150
                const y2 = targetIndex * 100 + 30
                
                return (
                  <g key={edge.id}>
                    <line
                      x1={x1} y1={y1}
                      x2={x2} y2={y2}
                      stroke="#9ca3af"
                      strokeWidth={2}
                      markerEnd="url(#arrowhead)"
                    />
                  </g>
                )
              })}
              <defs>
                <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
                  <polygon points="0 0, 10 3.5, 0 7" fill="#9ca3af" />
                </marker>
              </defs>
            </svg>
          </div>
        </div>
      </div>

      {/* Properties Panel */}
      {selectedNode && (
        <div className="w-72 bg-white rounded-lg shadow overflow-hidden">
          <div className="p-3 bg-gray-50 border-b">
            <h3 className="font-semibold text-gray-900 text-sm">Node Properties</h3>
          </div>
          <div className="p-4">
            {(() => {
              const node = nodes.find(n => n.id === selectedNode)
              if (!node) return null
              
              return (
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Name</label>
                    <input
                      type="text"
                      value={node.name}
                      onChange={(e) => {
                        setNodes(nodes.map(n => 
                          n.id === selectedNode ? { ...n, name: e.target.value } : n
                        ))
                      }}
                      className="w-full px-3 py-2 border border-gray-200 rounded text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">Type</label>
                    <p className="text-sm text-gray-900 bg-gray-100 px-3 py-2 rounded">{node.type}</p>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-500 mb-1">ID</label>
                    <p className="text-xs text-gray-500 font-mono">{node.id}</p>
                  </div>
                </div>
              )
            })()}
          </div>
        </div>
      )}

      {/* Execution Result Modal */}
      {executionResult && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-hidden">
            <div className="p-4 bg-gray-50 border-b flex justify-between items-center">
              <h3 className="font-semibold">Execution Result</h3>
              <button onClick={() => setExecutionResult(null)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[60vh]">
              <pre className="text-sm bg-gray-100 p-4 rounded overflow-x-auto">
                {JSON.stringify(executionResult, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
