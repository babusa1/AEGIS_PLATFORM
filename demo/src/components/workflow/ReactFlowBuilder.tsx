/**
 * React Flow Workflow Builder
 * 
 * Modern visual workflow builder using React Flow with Data Moat entity nodes.
 * Replaces custom canvas with industry-standard React Flow library.
 */

'use client';

import React, { useCallback, useState, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  Connection,
  NodeTypes,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';

import { Database, Bot, Zap, Code, Filter, Send, Layers } from 'lucide-react';

// Data Moat Entity Node Types
const DATA_MOAT_ENTITY_NODES = [
  { type: 'entity_patient', label: 'Query Patient', icon: '👤', color: '#3b82f6' },
  { type: 'entity_condition', label: 'Query Condition', icon: '🏥', color: '#ef4444' },
  { type: 'entity_medication', label: 'Query Medication', icon: '💊', color: '#10b981' },
  { type: 'entity_encounter', label: 'Query Encounter', icon: '📋', color: '#f59e0b' },
  { type: 'entity_claim', label: 'Query Claim', icon: '💰', color: '#8b5cf6' },
  { type: 'entity_denial', label: 'Query Denial', icon: '❌', color: '#ec4899' },
  { type: 'entity_lab_result', label: 'Query Lab Result', icon: '🧪', color: '#06b6d4' },
  { type: 'entity_vital', label: 'Query Vital', icon: '📊', color: '#14b8a6' },
  { type: 'entity_genomic_variant', label: 'Query Genomic Variant', icon: '🧬', color: '#a855f7' },
  { type: 'entity_workflow_execution', label: 'Query Workflow', icon: '⚙️', color: '#6366f1' },
];

// Custom Node Components
const DataMoatEntityNode = ({ data, selected }: any) => {
  const entityType = DATA_MOAT_ENTITY_NODES.find(e => e.type === data.entityType);
  const color = entityType?.color || '#6b7280';
  
  return (
    <div
      className={`px-4 py-3 shadow-lg rounded-lg border-2 ${
        selected ? 'border-blue-500' : 'border-gray-300'
      }`}
      style={{ backgroundColor: '#fff', minWidth: '200px' }}
    >
      <Handle type="target" position={Position.Top} />
      <div className="flex items-center gap-2">
        <span className="text-2xl">{entityType?.icon}</span>
        <div className="flex-1">
          <div className="font-semibold text-sm">{entityType?.label}</div>
          {data.entityId && (
            <div className="text-xs text-gray-500 mt-1">ID: {data.entityId}</div>
          )}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

const AgentNode = ({ data, selected }: any) => {
  return (
    <div
      className={`px-4 py-3 shadow-lg rounded-lg border-2 ${
        selected ? 'border-purple-500' : 'border-gray-300'
      }`}
      style={{ backgroundColor: '#fff', minWidth: '200px' }}
    >
      <Handle type="target" position={Position.Top} />
      <div className="flex items-center gap-2">
        <Bot className="w-5 h-5 text-purple-600" />
        <div className="flex-1">
          <div className="font-semibold text-sm">{data.label || 'AI Agent'}</div>
          {data.agentType && (
            <div className="text-xs text-gray-500 mt-1">{data.agentType}</div>
          )}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

const TriggerNode = ({ data, selected }: any) => {
  return (
    <div
      className={`px-4 py-3 shadow-lg rounded-lg border-2 ${
        selected ? 'border-yellow-500' : 'border-gray-300'
      }`}
      style={{ backgroundColor: '#fff', minWidth: '200px' }}
    >
      <div className="flex items-center gap-2">
        <Zap className="w-5 h-5 text-yellow-600" />
        <div className="flex-1">
          <div className="font-semibold text-sm">{data.label || 'Trigger'}</div>
          {data.triggerType && (
            <div className="text-xs text-gray-500 mt-1">{data.triggerType}</div>
          )}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

const LLMNode = ({ data, selected }: any) => {
  return (
    <div
      className={`px-4 py-3 shadow-lg rounded-lg border-2 ${
        selected ? 'border-green-500' : 'border-gray-300'
      }`}
      style={{ backgroundColor: '#fff', minWidth: '200px' }}
    >
      <Handle type="target" position={Position.Top} />
      <div className="flex items-center gap-2">
        <Code className="w-5 h-5 text-green-600" />
        <div className="flex-1">
          <div className="font-semibold text-sm">{data.label || 'LLM'}</div>
          {data.model && (
            <div className="text-xs text-gray-500 mt-1">{data.model}</div>
          )}
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} />
    </div>
  );
};

// Node type registry
const nodeTypes: NodeTypes = {
  data_moat_entity: DataMoatEntityNode,
  agent: AgentNode,
  trigger: TriggerNode,
  llm: LLMNode,
};

interface ReactFlowBuilderProps {
  initialNodes?: Node[];
  initialEdges?: Edge[];
  onSave?: (nodes: Node[], edges: Edge[]) => void;
  onExecute?: (nodes: Node[], edges: Edge[]) => void;
}

export default function ReactFlowBuilder({
  initialNodes = [],
  initialEdges = [],
  onSave,
  onExecute,
}: ReactFlowBuilderProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const addDataMoatNode = useCallback((entityType: string) => {
    const entity = DATA_MOAT_ENTITY_NODES.find(e => e.type === entityType);
    const newNode: Node = {
      id: `node-${Date.now()}`,
      type: 'data_moat_entity',
      position: { x: Math.random() * 400, y: Math.random() * 400 },
      data: {
        label: entity?.label || 'Data Moat Entity',
        entityType,
        entityId: '',
      },
    };
    setNodes((nds) => [...nds, newNode]);
  }, [setNodes]);

  const addAgentNode = useCallback((agentType: string) => {
    const newNode: Node = {
      id: `node-${Date.now()}`,
      type: 'agent',
      position: { x: Math.random() * 400, y: Math.random() * 400 },
      data: {
        label: agentType,
        agentType,
      },
    };
    setNodes((nds) => [...nds, newNode]);
  }, [setNodes]);

  const handleSave = useCallback(() => {
    if (onSave) {
      onSave(nodes, edges);
    }
  }, [nodes, edges, onSave]);

  const handleExecute = useCallback(() => {
    if (onExecute) {
      onExecute(nodes, edges);
    }
  }, [nodes, edges, onExecute]);

  return (
    <div className="flex h-screen">
      {/* Sidebar - Node Palette */}
      <div className="w-64 bg-gray-100 border-r p-4 overflow-y-auto">
        <h2 className="font-bold text-lg mb-4">Node Palette</h2>
        
        {/* Triggers */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
            <Zap className="w-4 h-4" /> Triggers
          </h3>
          <button
            onClick={() => {
              const newNode: Node = {
                id: `node-${Date.now()}`,
                type: 'trigger',
                position: { x: 100, y: 100 },
                data: { label: 'Webhook', triggerType: 'webhook' },
              };
              setNodes((nds) => [...nds, newNode]);
            }}
            className="w-full text-left px-3 py-2 bg-white rounded border hover:bg-gray-50 text-sm mb-1"
          >
            Webhook
          </button>
          <button
            onClick={() => {
              const newNode: Node = {
                id: `node-${Date.now()}`,
                type: 'trigger',
                position: { x: 100, y: 100 },
                data: { label: 'Schedule', triggerType: 'schedule' },
              };
              setNodes((nds) => [...nds, newNode]);
            }}
            className="w-full text-left px-3 py-2 bg-white rounded border hover:bg-gray-50 text-sm"
          >
            Schedule
          </button>
        </div>

        {/* Data Moat Entities */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
            <Database className="w-4 h-4" /> Data Moat (30+ Entities)
          </h3>
          <div className="space-y-1 max-h-64 overflow-y-auto">
            {DATA_MOAT_ENTITY_NODES.map((entity) => (
              <button
                key={entity.type}
                onClick={() => addDataMoatNode(entity.type)}
                className="w-full text-left px-3 py-2 bg-white rounded border hover:bg-gray-50 text-sm flex items-center gap-2"
              >
                <span>{entity.icon}</span>
                <span>{entity.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Agents */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
            <Bot className="w-4 h-4" /> AI Agents
          </h3>
          {['OncolifeAgent', 'ChaperoneCKMAgent', 'UnifiedViewAgent', 'TriageAgent', 'ActionAgent'].map((agent) => (
            <button
              key={agent}
              onClick={() => addAgentNode(agent)}
              className="w-full text-left px-3 py-2 bg-white rounded border hover:bg-gray-50 text-sm mb-1"
            >
              {agent}
            </button>
          ))}
        </div>

        {/* LLM */}
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-2 flex items-center gap-2">
            <Code className="w-4 h-4" /> LLM
          </h3>
          <button
            onClick={() => {
              const newNode: Node = {
                id: `node-${Date.now()}`,
                type: 'llm',
                position: { x: Math.random() * 400, y: Math.random() * 400 },
                data: { label: 'Generate', model: 'claude-3-sonnet' },
              };
              setNodes((nds) => [...nds, newNode]);
            }}
            className="w-full text-left px-3 py-2 bg-white rounded border hover:bg-gray-50 text-sm"
          >
            Generate Text
          </button>
        </div>

        {/* Actions */}
        <div className="mt-4 space-y-2">
          <button
            onClick={handleSave}
            className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Save Workflow
          </button>
          <button
            onClick={handleExecute}
            className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
          >
            Execute
          </button>
        </div>
      </div>

      {/* React Flow Canvas */}
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={(_, node) => setSelectedNode(node)}
          nodeTypes={nodeTypes}
          fitView
        >
          <Background />
          <Controls />
          <MiniMap />
        </ReactFlow>

        {/* Node Properties Panel */}
        {selectedNode && (
          <div className="absolute top-4 right-4 w-64 bg-white border rounded-lg shadow-lg p-4">
            <h3 className="font-semibold mb-2">Node Properties</h3>
            <div className="space-y-2 text-sm">
              <div>
                <label className="block text-gray-600">Type</label>
                <div className="text-gray-900">{selectedNode.type}</div>
              </div>
              {selectedNode.data.entityType && (
                <div>
                  <label className="block text-gray-600">Entity Type</label>
                  <div className="text-gray-900">{selectedNode.data.entityType}</div>
                </div>
              )}
              {selectedNode.data.agentType && (
                <div>
                  <label className="block text-gray-600">Agent</label>
                  <div className="text-gray-900">{selectedNode.data.agentType}</div>
                </div>
              )}
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="mt-4 w-full px-3 py-1 bg-gray-200 rounded hover:bg-gray-300 text-sm"
            >
              Close
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
