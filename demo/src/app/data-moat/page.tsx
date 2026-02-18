'use client'

import { useState, useEffect } from 'react'
import { 
  Database, Network, Search, Filter, TrendingUp, Users, FileText, 
  Activity, Heart, FlaskConical, Calendar, DollarSign, Shield, Dna,
  Image, MessageSquare, Clock, CheckCircle, AlertCircle, Loader2,
  ChevronRight, Eye, Code, Layers, Zap
} from 'lucide-react'

const API_BASE = 'http://localhost:8001'

interface EntityMetadata {
  table: string
  primary_key: string | null
  tenant_column: string | null
  description: string
  time_column?: string
}

interface EntityRegistry {
  entity_types: Array<{
    type: string
    metadata: EntityMetadata
    count?: number
  }>
  total_entities: number
}

interface EntitySample {
  id: string
  data: Record<string, any>
}

const entityCategories = {
  'Core Domain': ['tenant', 'user', 'api_key', 'data_source', 'audit_log'],
  'Clinical Domain': ['patient', 'condition', 'medication', 'encounter', 'procedure', 'observation', 'allergy_intolerance', 'clinical_note'],
  'Provider Domain': ['provider', 'organization', 'location'],
  'Financial Domain': ['claim', 'claim_line', 'denial', 'appeal', 'payment', 'coverage', 'payer', 'authorization'],
  'Time-Series Domain': ['vital', 'lab_result', 'wearable_metric'],
  'Genomics Domain': ['genomic_variant', 'genomic_report'],
  'Imaging Domain': ['imaging_study', 'imaging_series'],
  'SDOH Domain': ['sdoh_assessment'],
  'PRO Domain': ['pro_response'],
  'Messaging Domain': ['message'],
  'Scheduling Domain': ['appointment', 'schedule'],
  'Workflow Domain': ['workflow_definition', 'workflow_execution'],
  'Security Domain': ['consent', 'btg_session', 'sync_job'],
}

const entityIcons: Record<string, any> = {
  patient: Users,
  claim: FileText,
  denial: AlertCircle,
  vital: Heart,
  lab_result: FlaskConical,
  encounter: Calendar,
  medication: Activity,
  provider: Users,
  organization: Shield,
  workflow_definition: Network,
  workflow_execution: Zap,
  genomic_variant: Dna,
  imaging_study: Image,
  message: MessageSquare,
  appointment: Clock,
}

const entityColors: Record<string, string> = {
  'Core Domain': 'bg-gray-100 text-gray-700',
  'Clinical Domain': 'bg-blue-100 text-blue-700',
  'Provider Domain': 'bg-green-100 text-green-700',
  'Financial Domain': 'bg-yellow-100 text-yellow-700',
  'Time-Series Domain': 'bg-purple-100 text-purple-700',
  'Genomics Domain': 'bg-pink-100 text-pink-700',
  'Imaging Domain': 'bg-indigo-100 text-indigo-700',
  'SDOH Domain': 'bg-orange-100 text-orange-700',
  'PRO Domain': 'bg-teal-100 text-teal-700',
  'Messaging Domain': 'bg-cyan-100 text-cyan-700',
  'Scheduling Domain': 'bg-emerald-100 text-emerald-700',
  'Workflow Domain': 'bg-violet-100 text-violet-700',
  'Security Domain': 'bg-red-100 text-red-700',
}

export default function DataMoatExplorer() {
  const [registry, setRegistry] = useState<EntityRegistry | null>(null)
  const [selectedEntity, setSelectedEntity] = useState<string | null>(null)
  const [entitySamples, setEntitySamples] = useState<Record<string, EntitySample[]>>({})
  const [loading, setLoading] = useState(true)
  const [loadingSamples, setLoadingSamples] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchRegistry()
  }, [])

  const fetchRegistry = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/v1/entities/registry`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setRegistry(data)
    } catch (err: any) {
      console.error('Failed to fetch registry:', err)
      setError(`Cannot connect to API at ${API_BASE}. Make sure the backend is running.`)
      // Use mock data for demo
      setRegistry({
        entity_types: Object.values(entityCategories).flat().map(type => ({
          type,
          metadata: {
            table: `${type}s`,
            primary_key: 'id',
            tenant_column: 'tenant_id',
            description: `${type} entity`,
          },
          count: Math.floor(Math.random() * 1000),
        })),
        total_entities: 50000,
      })
    } finally {
      setLoading(false)
    }
  }

  const fetchEntitySamples = async (entityType: string) => {
    if (entitySamples[entityType]) return
    
    setLoadingSamples(entityType)
    try {
      const res = await fetch(`${API_BASE}/v1/entities/${entityType}?limit=5`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setEntitySamples({
        ...entitySamples,
        [entityType]: data.entities || [],
      })
    } catch (err: any) {
      console.error(`Failed to fetch samples for ${entityType}:`, err)
      // Mock sample data
      setEntitySamples({
        ...entitySamples,
        [entityType]: [{
          id: `sample-${entityType}-1`,
          data: {
            id: `sample-${entityType}-1`,
            name: `Sample ${entityType}`,
            created_at: new Date().toISOString(),
            ...(entityType === 'patient' ? { mrn: 'MRN001', name: 'John Doe' } : {}),
            ...(entityType === 'claim' ? { claim_id: 'CLM001', amount: 1500.00, status: 'pending' } : {}),
          },
        }],
      })
    } finally {
      setLoadingSamples(null)
    }
  }

  const filteredEntities = registry?.entity_types.filter(e => {
    const matchesSearch = !searchQuery || 
      e.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      e.metadata.description.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesCategory = !selectedCategory || 
      entityCategories[selectedCategory as keyof typeof entityCategories]?.includes(e.type)
    return matchesSearch && matchesCategory
  }) || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Layers className="w-7 h-7 text-blue-600" />
            VeritOS Data Moat Explorer
          </h1>
          <p className="text-gray-500 mt-1">
            Unified data layer with 30+ entity types across 7 databases
          </p>
        </div>
        {registry && (
          <div className="text-right">
            <p className="text-3xl font-bold text-blue-600">{registry.total_entities.toLocaleString()}</p>
            <p className="text-sm text-gray-500">Total Entities</p>
          </div>
        )}
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-700 px-4 py-3 rounded-lg flex items-center gap-3">
          <AlertCircle className="w-5 h-5" />
          <div className="flex-1">
            <p className="font-medium">Demo Mode</p>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      {registry && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg shadow p-4 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-90">Entity Types</p>
                <p className="text-2xl font-bold">{registry.entity_types.length}</p>
              </div>
              <Database className="w-8 h-8 opacity-50" />
            </div>
          </div>
          <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-lg shadow p-4 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-90">Databases</p>
                <p className="text-2xl font-bold">7</p>
              </div>
              <Network className="w-8 h-8 opacity-50" />
            </div>
          </div>
          <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-lg shadow p-4 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-90">Data Sources</p>
                <p className="text-2xl font-bold">30+</p>
              </div>
              <TrendingUp className="w-8 h-8 opacity-50" />
            </div>
          </div>
          <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-lg shadow p-4 text-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm opacity-90">Unified API</p>
                <p className="text-lg font-bold">Generic</p>
              </div>
              <Code className="w-8 h-8 opacity-50" />
            </div>
          </div>
        </div>
      )}

      {/* Search and Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search entity types..."
              className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            />
          </div>
          <select
            value={selectedCategory || ''}
            onChange={(e) => setSelectedCategory(e.target.value || null)}
            className="px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/20"
          >
            <option value="">All Categories</option>
            {Object.keys(entityCategories).map(cat => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Entity Grid by Category */}
      {loading ? (
        <div className="bg-white rounded-lg shadow p-12 flex items-center justify-center">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(entityCategories).map(([category, types]) => {
            const categoryEntities = filteredEntities.filter(e => types.includes(e.type))
            if (categoryEntities.length === 0) return null

            return (
              <div key={category} className="bg-white rounded-lg shadow">
                <div className={`p-4 border-b ${entityColors[category] || 'bg-gray-100'}`}>
                  <h2 className="font-semibold text-lg">{category}</h2>
                  <p className="text-sm opacity-75 mt-1">{categoryEntities.length} entity types</p>
                </div>
                <div className="p-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {categoryEntities.map(entity => {
                    const Icon = entityIcons[entity.type] || Database
                    const isSelected = selectedEntity === entity.type
                    const hasSamples = !!entitySamples[entity.type]

                    return (
                      <div
                        key={entity.type}
                        onClick={() => {
                          setSelectedEntity(entity.type)
                          if (!hasSamples) fetchEntitySamples(entity.type)
                        }}
                        className={`p-4 border-2 rounded-lg cursor-pointer transition-all hover:shadow-md ${
                          isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                              <Icon className="w-5 h-5 text-blue-600" />
                            </div>
                            <div>
                              <h3 className="font-semibold text-gray-900 capitalize">
                                {entity.type.replace(/_/g, ' ')}
                              </h3>
                              <p className="text-xs text-gray-500 font-mono">{entity.metadata.table}</p>
                            </div>
                          </div>
                          {isSelected && <ChevronRight className="w-5 h-5 text-blue-600" />}
                        </div>
                        <p className="text-sm text-gray-600 mb-2">{entity.metadata.description}</p>
                        <div className="flex gap-2 flex-wrap">
                          {entity.metadata.primary_key && (
                            <span className="text-xs px-2 py-1 bg-green-100 text-green-700 rounded">
                              PK: {entity.metadata.primary_key}
                            </span>
                          )}
                          {entity.metadata.time_column && (
                            <span className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded">
                              Time-series
                            </span>
                          )}
                          {entity.count !== undefined && (
                            <span className="text-xs px-2 py-1 bg-gray-100 text-gray-700 rounded">
                              {entity.count.toLocaleString()} records
                            </span>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Entity Detail Panel */}
      {selectedEntity && (
        <div className="bg-white rounded-lg shadow-lg border-2 border-blue-500">
          <div className="p-4 bg-blue-50 border-b flex justify-between items-center">
            <div>
              <h2 className="font-semibold text-lg capitalize">
                {selectedEntity.replace(/_/g, ' ')}
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                {registry?.entity_types.find(e => e.type === selectedEntity)?.metadata.description}
              </p>
            </div>
            <button
              onClick={() => setSelectedEntity(null)}
              className="text-gray-400 hover:text-gray-600"
            >
              ×
            </button>
          </div>
          <div className="p-4">
            {/* Metadata */}
            <div className="mb-4">
              <h3 className="font-semibold text-sm text-gray-700 mb-2">Metadata</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-xs text-gray-500">Table</p>
                  <p className="font-mono text-sm">{registry?.entity_types.find(e => e.type === selectedEntity)?.metadata.table}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-500">Primary Key</p>
                  <p className="font-mono text-sm">{registry?.entity_types.find(e => e.type === selectedEntity)?.metadata.primary_key || 'N/A'}</p>
                </div>
              </div>
            </div>

            {/* Sample Data */}
            <div>
              <div className="flex justify-between items-center mb-2">
                <h3 className="font-semibold text-sm text-gray-700">Sample Data</h3>
                {loadingSamples === selectedEntity ? (
                  <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                ) : (
                  <button
                    onClick={() => fetchEntitySamples(selectedEntity)}
                    className="text-xs text-blue-600 hover:underline"
                  >
                    Refresh
                  </button>
                )}
              </div>
              {entitySamples[selectedEntity] ? (
                <div className="space-y-2">
                  {entitySamples[selectedEntity].map((sample, i) => (
                    <div key={i} className="bg-gray-50 rounded p-3 border border-gray-200">
                      <pre className="text-xs overflow-x-auto">
                        {JSON.stringify(sample.data, null, 2)}
                      </pre>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="bg-gray-50 rounded p-4 text-center text-sm text-gray-500">
                  Click to load sample data
                </div>
              )}
            </div>

            {/* API Example */}
            <div className="mt-4 pt-4 border-t">
              <h3 className="font-semibold text-sm text-gray-700 mb-2">API Access</h3>
              <div className="bg-gray-900 text-green-400 rounded p-3 font-mono text-xs overflow-x-auto">
                <div>GET {API_BASE}/v1/entities/{selectedEntity}</div>
                <div className="mt-1 text-gray-400">GET {API_BASE}/v1/entities/{selectedEntity}/&#123;id&#125;</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
