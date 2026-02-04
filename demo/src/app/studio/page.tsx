'use client';

import React, { useState, useCallback, useRef, useEffect } from 'react';
import {
  Play,
  Save,
  Download,
  Upload,
  Trash2,
  Plus,
  Settings,
  Zap,
  Database,
  Bot,
  GitBranch,
  Filter,
  Code,
  Send,
  AlertCircle,
  CheckCircle,
  Clock,
  Layers,
  Search,
  ChevronRight,
  ChevronDown,
  GripVertical,
  X,
  Copy,
  Maximize2,
  Activity,
  FileText,
} from 'lucide-react';

// Types
interface Node {
  id: string;
  type: string;
  category: string;
  name: string;
  x: number;
  y: number;
  config: Record<string, any>;
  inputs: string[];
  outputs: string[];
}

interface Edge {
  id: string;
  source: string;
  target: string;
  sourceHandle?: string;
  targetHandle?: string;
}

interface WorkflowDefinition {
  id: string;
  name: string;
  description: string;
  nodes: Node[];
  edges: Edge[];
}

// Node type definitions
const NODE_TYPES = {
  triggers: {
    label: 'Triggers',
    icon: Zap,
    color: 'bg-yellow-500',
    nodes: [
      { type: 'webhook', name: 'Webhook', description: 'HTTP webhook trigger' },
      { type: 'schedule', name: 'Schedule', description: 'Cron/interval trigger' },
      { type: 'event', name: 'Event', description: 'Kafka event trigger' },
      { type: 'manual', name: 'Manual', description: 'Manual trigger' },
    ],
  },
  data_moat: {
    label: 'Data Moat',
    icon: Database,
    color: 'bg-blue-500',
    nodes: [
      { type: 'query_patients', name: 'Query Patients', description: 'Search patients' },
      { type: 'query_denials', name: 'Query Denials', description: 'Search denials' },
      { type: 'query_claims', name: 'Query Claims', description: 'Search claims' },
      { type: 'query_vitals', name: 'Query Vitals', description: 'Get vital signs' },
      { type: 'query_labs', name: 'Query Labs', description: 'Get lab results' },
      { type: 'graph_query', name: 'Graph Query', description: 'Query knowledge graph' },
      { type: 'vector_search', name: 'Vector Search', description: 'Semantic search' },
    ],
  },
  agents: {
    label: 'AI Agents',
    icon: Bot,
    color: 'bg-purple-500',
    nodes: [
      { type: 'patient_agent', name: 'Patient Agent', description: '360 view analysis' },
      { type: 'denial_agent', name: 'Denial Agent', description: 'Denial management' },
      { type: 'triage_agent', name: 'Triage Agent', description: 'Clinical triage' },
      { type: 'insight_agent', name: 'Insight Agent', description: 'Pattern discovery' },
      { type: 'custom_agent', name: 'Custom Agent', description: 'Custom LLM agent' },
    ],
  },
  llm: {
    label: 'LLM',
    icon: Zap,
    color: 'bg-green-500',
    nodes: [
      { type: 'llm_generate', name: 'Generate', description: 'Text generation' },
      { type: 'llm_classify', name: 'Classify', description: 'Classification' },
      { type: 'llm_extract', name: 'Extract', description: 'Entity extraction' },
      { type: 'llm_summarize', name: 'Summarize', description: 'Summarization' },
    ],
  },
  logic: {
    label: 'Logic',
    icon: GitBranch,
    color: 'bg-orange-500',
    nodes: [
      { type: 'condition', name: 'If/Else', description: 'Conditional branching' },
      { type: 'switch', name: 'Switch', description: 'Multi-way branch' },
      { type: 'loop', name: 'Loop', description: 'Iterate over items' },
      { type: 'merge', name: 'Merge', description: 'Merge branches' },
      { type: 'parallel', name: 'Parallel', description: 'Parallel execution' },
    ],
  },
  transform: {
    label: 'Transform',
    icon: Filter,
    color: 'bg-cyan-500',
    nodes: [
      { type: 'filter', name: 'Filter', description: 'Filter data' },
      { type: 'map', name: 'Map', description: 'Transform items' },
      { type: 'aggregate', name: 'Aggregate', description: 'Aggregate data' },
      { type: 'sort', name: 'Sort', description: 'Sort items' },
    ],
  },
  actions: {
    label: 'Actions',
    icon: Send,
    color: 'bg-red-500',
    nodes: [
      { type: 'http_request', name: 'HTTP Request', description: 'Make API call' },
      { type: 'send_email', name: 'Send Email', description: 'Send email' },
      { type: 'send_slack', name: 'Send Slack', description: 'Slack message' },
      { type: 'generate_appeal', name: 'Generate Appeal', description: 'Create appeal letter' },
      { type: 'send_alert', name: 'Send Alert', description: 'Send alert notification' },
    ],
  },
  code: {
    label: 'Code',
    icon: Code,
    color: 'bg-gray-500',
    nodes: [
      { type: 'python', name: 'Python', description: 'Run Python code' },
      { type: 'javascript', name: 'JavaScript', description: 'Run JS code' },
      { type: 'sql', name: 'SQL', description: 'Run SQL query' },
    ],
  },
};

// Node Component
const WorkflowNode: React.FC<{
  node: Node;
  selected: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onDragStart: (e: React.DragEvent) => void;
}> = ({ node, selected, onSelect, onDelete, onDragStart }) => {
  const category = Object.entries(NODE_TYPES).find(([_, cat]) =>
    cat.nodes.some(n => n.type === node.type)
  );
  
  const Icon = category?.[1]?.icon || Zap;
  const color = category?.[1]?.color || 'bg-gray-500';
  
  return (
    <div
      className={`absolute cursor-move bg-white rounded-lg shadow-lg border-2 transition-all ${
        selected ? 'border-blue-500 shadow-xl' : 'border-gray-200'
      }`}
      style={{ left: node.x, top: node.y, width: 200 }}
      onClick={(e) => {
        e.stopPropagation();
        onSelect();
      }}
      draggable
      onDragStart={onDragStart}
    >
      {/* Header */}
      <div className={`${color} text-white px-3 py-2 rounded-t-md flex items-center gap-2`}>
        <GripVertical className="w-4 h-4 cursor-grab" />
        <Icon className="w-4 h-4" />
        <span className="flex-1 text-sm font-medium truncate">{node.name}</span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="hover:bg-white/20 rounded p-0.5"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
      
      {/* Body */}
      <div className="p-3">
        <p className="text-xs text-gray-500 mb-2">{node.type}</p>
        
        {/* Input handles */}
        <div className="flex items-center gap-1 mb-2">
          <div className="w-3 h-3 bg-blue-400 rounded-full border-2 border-white shadow" />
          <span className="text-xs text-gray-400">input</span>
        </div>
        
        {/* Output handles */}
        <div className="flex items-center justify-end gap-1">
          <span className="text-xs text-gray-400">output</span>
          <div className="w-3 h-3 bg-green-400 rounded-full border-2 border-white shadow" />
        </div>
      </div>
    </div>
  );
};

// Main Studio Component
export default function WorkflowStudio() {
  const [workflow, setWorkflow] = useState<WorkflowDefinition>({
    id: 'new-workflow',
    name: 'Untitled Workflow',
    description: '',
    nodes: [],
    edges: [],
  });
  
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [expandedCategories, setExpandedCategories] = useState<string[]>(Object.keys(NODE_TYPES));
  const [searchTerm, setSearchTerm] = useState('');
  const [executing, setExecuting] = useState(false);
  const [executionResult, setExecutionResult] = useState<any>(null);
  const [showResults, setShowResults] = useState(false);
  
  const canvasRef = useRef<HTMLDivElement>(null);
  
  // Add node to canvas
  const addNode = (type: string, name: string, category: string) => {
    const newNode: Node = {
      id: `node-${Date.now()}`,
      type,
      category,
      name,
      x: 300 + Math.random() * 100,
      y: 100 + workflow.nodes.length * 120,
      config: {},
      inputs: ['default'],
      outputs: ['default'],
    };
    
    setWorkflow(prev => ({
      ...prev,
      nodes: [...prev.nodes, newNode],
    }));
  };
  
  // Delete node
  const deleteNode = (nodeId: string) => {
    setWorkflow(prev => ({
      ...prev,
      nodes: prev.nodes.filter(n => n.id !== nodeId),
      edges: prev.edges.filter(e => e.source !== nodeId && e.target !== nodeId),
    }));
    if (selectedNode === nodeId) {
      setSelectedNode(null);
    }
  };
  
  // Handle node drag
  const handleNodeDrag = (nodeId: string, e: React.DragEvent) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left - 100;
    const y = e.clientY - rect.top - 30;
    
    setWorkflow(prev => ({
      ...prev,
      nodes: prev.nodes.map(n =>
        n.id === nodeId ? { ...n, x: Math.max(0, x), y: Math.max(0, y) } : n
      ),
    }));
  };
  
  // Auto-connect nodes
  const autoConnect = () => {
    const sortedNodes = [...workflow.nodes].sort((a, b) => a.y - b.y);
    const newEdges: Edge[] = [];
    
    for (let i = 0; i < sortedNodes.length - 1; i++) {
      newEdges.push({
        id: `edge-${sortedNodes[i].id}-${sortedNodes[i + 1].id}`,
        source: sortedNodes[i].id,
        target: sortedNodes[i + 1].id,
      });
    }
    
    setWorkflow(prev => ({ ...prev, edges: newEdges }));
  };
  
  // Execute workflow
  const executeWorkflow = async () => {
    setExecuting(true);
    setShowResults(true);
    
    try {
      const response = await fetch('http://localhost:8001/v1/orchestrator/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_id: workflow.id,
          inputs: { query: 'Execute workflow' },
          definition: {
            id: workflow.id,
            name: workflow.name,
            nodes: workflow.nodes.map(n => ({
              id: n.id,
              type: n.type.toUpperCase(),
              name: n.name,
              tool_id: n.type,
              config: n.config,
            })),
            edges: workflow.edges.map(e => ({
              source: e.source,
              target: e.target,
            })),
          },
        }),
      });
      
      const result = await response.json();
      setExecutionResult(result);
    } catch (error) {
      setExecutionResult({ error: String(error) });
    } finally {
      setExecuting(false);
    }
  };
  
  // Save workflow
  const saveWorkflow = async () => {
    try {
      await fetch('http://localhost:8001/v1/orchestrator/workflows', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: workflow.id,
          name: workflow.name,
          description: workflow.description,
          nodes: workflow.nodes.map(n => ({
            id: n.id,
            type: n.type.toUpperCase(),
            name: n.name,
            tool_id: n.type,
            config: n.config,
          })),
          edges: workflow.edges.map(e => ({
            source: e.source,
            target: e.target,
          })),
        }),
      });
      alert('Workflow saved!');
    } catch (error) {
      alert('Failed to save workflow');
    }
  };
  
  // Filter nodes by search
  const filteredNodeTypes = Object.entries(NODE_TYPES).map(([key, category]) => ({
    key,
    ...category,
    nodes: category.nodes.filter(n =>
      n.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      n.description.toLowerCase().includes(searchTerm.toLowerCase())
    ),
  })).filter(cat => cat.nodes.length > 0);
  
  return (
    <div className="flex h-screen bg-gray-100">
      {/* Left Sidebar - Node Palette */}
      <div className="w-64 bg-white border-r shadow-sm flex flex-col">
        <div className="p-4 border-b">
          <h2 className="font-bold text-lg mb-2">Workflow Studio</h2>
          <div className="relative">
            <Search className="w-4 h-4 absolute left-2 top-2.5 text-gray-400" />
            <input
              type="text"
              placeholder="Search nodes..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-8 pr-3 py-2 text-sm border rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-2">
          {filteredNodeTypes.map(category => (
            <div key={category.key} className="mb-2">
              <button
                onClick={() => {
                  setExpandedCategories(prev =>
                    prev.includes(category.key)
                      ? prev.filter(c => c !== category.key)
                      : [...prev, category.key]
                  );
                }}
                className="w-full flex items-center gap-2 px-2 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded"
              >
                {expandedCategories.includes(category.key) ? (
                  <ChevronDown className="w-4 h-4" />
                ) : (
                  <ChevronRight className="w-4 h-4" />
                )}
                <category.icon className="w-4 h-4" />
                {category.label}
                <span className="ml-auto text-xs text-gray-400">{category.nodes.length}</span>
              </button>
              
              {expandedCategories.includes(category.key) && (
                <div className="ml-4 mt-1 space-y-1">
                  {category.nodes.map(node => (
                    <button
                      key={node.type}
                      onClick={() => addNode(node.type, node.name, category.key)}
                      className="w-full flex items-center gap-2 px-2 py-1.5 text-sm text-gray-600 hover:bg-blue-50 hover:text-blue-700 rounded transition-colors"
                    >
                      <div className={`w-2 h-2 rounded-full ${category.color}`} />
                      <span className="flex-1 text-left">{node.name}</span>
                      <Plus className="w-3 h-3 opacity-0 group-hover:opacity-100" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
        
        {/* Quick Stats */}
        <div className="p-3 border-t bg-gray-50 text-xs text-gray-500">
          <div className="flex justify-between">
            <span>Nodes: {workflow.nodes.length}</span>
            <span>Edges: {workflow.edges.length}</span>
          </div>
        </div>
      </div>
      
      {/* Main Canvas Area */}
      <div className="flex-1 flex flex-col">
        {/* Toolbar */}
        <div className="bg-white border-b px-4 py-2 flex items-center gap-4">
          <input
            type="text"
            value={workflow.name}
            onChange={(e) => setWorkflow(prev => ({ ...prev, name: e.target.value }))}
            className="text-lg font-semibold bg-transparent border-b border-transparent hover:border-gray-300 focus:border-blue-500 focus:outline-none px-1"
          />
          
          <div className="flex-1" />
          
          <button
            onClick={autoConnect}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            <GitBranch className="w-4 h-4" />
            Auto-Connect
          </button>
          
          <button
            onClick={saveWorkflow}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg"
          >
            <Save className="w-4 h-4" />
            Save
          </button>
          
          <button
            onClick={executeWorkflow}
            disabled={executing || workflow.nodes.length === 0}
            className="flex items-center gap-1 px-4 py-1.5 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
          >
            {executing ? (
              <>
                <Clock className="w-4 h-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Execute
              </>
            )}
          </button>
        </div>
        
        {/* Canvas */}
        <div
          ref={canvasRef}
          className="flex-1 relative overflow-auto bg-gray-50"
          style={{
            backgroundImage: 'radial-gradient(circle, #ddd 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }}
          onClick={() => setSelectedNode(null)}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            const nodeId = e.dataTransfer.getData('nodeId');
            if (nodeId) {
              handleNodeDrag(nodeId, e);
            }
          }}
        >
          {/* Edges (SVG) */}
          <svg className="absolute inset-0 pointer-events-none" style={{ width: '100%', height: '100%' }}>
            {workflow.edges.map(edge => {
              const sourceNode = workflow.nodes.find(n => n.id === edge.source);
              const targetNode = workflow.nodes.find(n => n.id === edge.target);
              
              if (!sourceNode || !targetNode) return null;
              
              const startX = sourceNode.x + 200;
              const startY = sourceNode.y + 60;
              const endX = targetNode.x;
              const endY = targetNode.y + 40;
              
              const midX = (startX + endX) / 2;
              
              return (
                <g key={edge.id}>
                  <path
                    d={`M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`}
                    fill="none"
                    stroke="#94a3b8"
                    strokeWidth="2"
                    markerEnd="url(#arrowhead)"
                  />
                </g>
              );
            })}
            <defs>
              <marker
                id="arrowhead"
                markerWidth="10"
                markerHeight="7"
                refX="9"
                refY="3.5"
                orient="auto"
              >
                <polygon points="0 0, 10 3.5, 0 7" fill="#94a3b8" />
              </marker>
            </defs>
          </svg>
          
          {/* Nodes */}
          {workflow.nodes.map(node => (
            <WorkflowNode
              key={node.id}
              node={node}
              selected={selectedNode === node.id}
              onSelect={() => setSelectedNode(node.id)}
              onDelete={() => deleteNode(node.id)}
              onDragStart={(e) => {
                e.dataTransfer.setData('nodeId', node.id);
              }}
            />
          ))}
          
          {/* Empty state */}
          {workflow.nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center text-gray-400">
                <Layers className="w-12 h-12 mx-auto mb-3" />
                <p className="text-lg font-medium">No nodes yet</p>
                <p className="text-sm">Click nodes from the left panel to add them</p>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Right Sidebar - Results/Config */}
      {showResults && (
        <div className="w-80 bg-white border-l shadow-sm flex flex-col">
          <div className="p-3 border-b flex items-center justify-between">
            <h3 className="font-semibold">Execution Results</h3>
            <button
              onClick={() => setShowResults(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-3">
            {executing ? (
              <div className="flex flex-col items-center justify-center py-8">
                <Activity className="w-8 h-8 text-blue-500 animate-pulse mb-2" />
                <p className="text-sm text-gray-500">Executing workflow...</p>
              </div>
            ) : executionResult ? (
              <div>
                {executionResult.error ? (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <div className="flex items-center gap-2 text-red-600 mb-2">
                      <AlertCircle className="w-4 h-4" />
                      <span className="font-medium">Error</span>
                    </div>
                    <p className="text-sm text-red-700">{executionResult.error}</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                      <div className="flex items-center gap-2 text-green-600 mb-1">
                        <CheckCircle className="w-4 h-4" />
                        <span className="font-medium">Completed</span>
                      </div>
                      <p className="text-xs text-green-700">
                        {executionResult.duration_ms}ms
                      </p>
                    </div>
                    
                    {executionResult.trace && (
                      <div>
                        <h4 className="text-sm font-medium mb-2">Execution Trace</h4>
                        <div className="space-y-2">
                          {executionResult.trace.map((step: any, i: number) => (
                            <div key={i} className="bg-gray-50 rounded p-2 text-xs">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-medium">{step.node_id}</span>
                                <span className="text-gray-400">{step.duration_ms}ms</span>
                              </div>
                              {step.output && (
                                <pre className="text-gray-600 overflow-x-auto">
                                  {JSON.stringify(step.output, null, 2).slice(0, 200)}...
                                </pre>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    
                    <div>
                      <h4 className="text-sm font-medium mb-2">Output</h4>
                      <pre className="bg-gray-50 p-2 rounded text-xs overflow-x-auto max-h-64">
                        {JSON.stringify(executionResult.outputs || executionResult, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-400 text-center py-8">
                Execute workflow to see results
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
