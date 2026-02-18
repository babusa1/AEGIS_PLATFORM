'use client'

import { useState, useEffect } from 'react'
import { 
  Upload, Database, Play, CheckCircle, AlertCircle, Loader2, 
  ArrowRight, Filter, Shield, Code, Network, Zap, FileText,
  TrendingUp, Clock, Eye, RefreshCw
} from 'lucide-react'

const API_BASE = 'http://localhost:8001'

interface PipelineStep {
  name: string
  status: 'pending' | 'running' | 'completed' | 'error'
  duration?: number
  recordsProcessed?: number
  errors?: string[]
}

interface IngestionResult {
  status: 'success' | 'error'
  counts: Record<string, number>
  message: string
  pipelineSteps?: PipelineStep[]
  beforeCleaning?: any
  afterCleaning?: any
}

export default function IngestionPage() {
  const [mode, setMode] = useState<'fhir' | 'synthetic'>('synthetic')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<IngestionResult | null>(null)
  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>([])
  const [syntheticConfig, setSyntheticConfig] = useState({
    numPatients: 100,
    denialRate: 0.15,
  })

  const pipelineFlow = [
    { name: 'Receive Payload', icon: Upload, color: 'bg-blue-500' },
    { name: 'Parse & Transform', icon: Code, color: 'bg-purple-500' },
    { name: 'MPI Matching', icon: Network, color: 'bg-green-500' },
    { name: 'Validate & Clean', icon: Filter, color: 'bg-yellow-500' },
    { name: 'Write to Data Moat', icon: Database, color: 'bg-indigo-500' },
    { name: 'Index in Graph', icon: Network, color: 'bg-pink-500' },
    { name: 'Complete', icon: CheckCircle, color: 'bg-green-600' },
  ]

  const handleIngest = async () => {
    setIsLoading(true)
    setResult(null)
    
    // Initialize pipeline steps
    const steps: PipelineStep[] = pipelineFlow.map((step, i) => ({
      name: step.name,
      status: i === 0 ? 'running' : 'pending',
    }))
    setPipelineSteps(steps)

    // Simulate pipeline execution
    for (let i = 0; i < steps.length; i++) {
      await new Promise(resolve => setTimeout(resolve, 800))
      
      const updatedSteps = [...steps]
      updatedSteps[i].status = 'completed'
      updatedSteps[i].duration = Math.random() * 500 + 200
      updatedSteps[i].recordsProcessed = i === 3 ? syntheticConfig.numPatients : undefined
      
      if (i < steps.length - 1) {
        updatedSteps[i + 1].status = 'running'
      }
      
      setPipelineSteps(updatedSteps)
      steps[i] = updatedSteps[i]
    }

    // Final result
    await new Promise(resolve => setTimeout(resolve, 500))
    
    setResult({
      status: 'success',
      counts: {
        patients: syntheticConfig.numPatients,
        providers: 25,
        organizations: 10,
        encounters: syntheticConfig.numPatients * 3,
        diagnoses: syntheticConfig.numPatients * 5,
        procedures: syntheticConfig.numPatients * 2,
        claims: syntheticConfig.numPatients * 2,
        denials: Math.round(syntheticConfig.numPatients * 2 * syntheticConfig.denialRate),
      },
      message: 'Data ingested successfully!',
      pipelineSteps: steps,
      beforeCleaning: {
        totalRecords: syntheticConfig.numPatients * 10,
        invalidRecords: Math.floor(syntheticConfig.numPatients * 0.1),
        duplicateRecords: Math.floor(syntheticConfig.numPatients * 0.05),
        missingFields: Math.floor(syntheticConfig.numPatients * 0.15),
      },
      afterCleaning: {
        totalRecords: syntheticConfig.numPatients * 10,
        validRecords: Math.floor(syntheticConfig.numPatients * 9.5),
        normalizedRecords: Math.floor(syntheticConfig.numPatients * 9.5),
        errors: 0,
      },
    })

    setIsLoading(false)
  }

  const getStepIcon = (step: PipelineStep) => {
    if (step.status === 'completed') return CheckCircle
    if (step.status === 'running') return Loader2
    if (step.status === 'error') return AlertCircle
    return Clock
  }

  const getStepColor = (step: PipelineStep) => {
    if (step.status === 'completed') return 'bg-green-500'
    if (step.status === 'running') return 'bg-blue-500'
    if (step.status === 'error') return 'bg-red-500'
    return 'bg-gray-300'
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Data Ingestion Pipeline</h1>
        <p className="text-gray-500 mt-1">
          Unified ingestion: source_type + payload → connector → parse → validate → write to Data Moat
        </p>
      </div>

      {/* Mode Selection */}
      <div className="flex gap-4">
        <button
          onClick={() => setMode('fhir')}
          className={`flex-1 card card-hover ${mode === 'fhir' ? 'ring-2 ring-aegis-primary' : ''}`}
        >
          <Upload className="w-8 h-8 text-aegis-primary mb-3" />
          <h3 className="font-semibold">Upload FHIR Bundle</h3>
          <p className="text-sm text-gray-500 mt-1">Import FHIR R4 compliant data</p>
        </button>
        <button
          onClick={() => setMode('synthetic')}
          className={`flex-1 card card-hover ${mode === 'synthetic' ? 'ring-2 ring-aegis-primary' : ''}`}
        >
          <Database className="w-8 h-8 text-aegis-primary mb-3" />
          <h3 className="font-semibold">Generate Synthetic Data</h3>
          <p className="text-sm text-gray-500 mt-1">Create realistic demo data</p>
        </button>
      </div>

      {/* Configuration */}
      {mode === 'synthetic' && (
        <div className="card">
          <h3 className="font-semibold mb-4">Synthetic Data Configuration</h3>
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Number of Patients
              </label>
              <input
                type="number"
                value={syntheticConfig.numPatients}
                onChange={(e) => setSyntheticConfig({...syntheticConfig, numPatients: parseInt(e.target.value)})}
                className="w-full px-4 py-2 border border-gray-200 rounded-lg"
                min={10}
                max={1000}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Denial Rate ({Math.round(syntheticConfig.denialRate * 100)}%)
              </label>
              <input
                type="range"
                value={syntheticConfig.denialRate}
                onChange={(e) => setSyntheticConfig({...syntheticConfig, denialRate: parseFloat(e.target.value)})}
                className="w-full"
                min={0}
                max={0.5}
                step={0.01}
              />
            </div>
          </div>
          <button
            onClick={handleIngest}
            disabled={isLoading}
            className="mt-6 w-full py-3 bg-aegis-primary text-white rounded-lg hover:bg-aegis-primary/90 disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Processing Pipeline...
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                Generate & Ingest Data
              </>
            )}
          </button>
        </div>
      )}

      {/* Pipeline Flow Visualization */}
      {(isLoading || result) && (
        <div className="card">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-500" />
            Ingestion Pipeline Flow
          </h3>
          <div className="relative">
            {/* Pipeline Steps */}
            <div className="flex items-center justify-between overflow-x-auto pb-4">
              {pipelineFlow.map((step, index) => {
                const stepStatus = pipelineSteps[index]?.status || 'pending'
                const StepIcon = getStepIcon(pipelineSteps[index] || { name: step.name, status: 'pending' })
                const isActive = stepStatus === 'running' || stepStatus === 'completed'
                const isCompleted = stepStatus === 'completed'
                
                return (
                  <div key={step.name} className="flex items-center flex-shrink-0">
                    <div className="flex flex-col items-center">
                      <div className={`w-16 h-16 rounded-full flex items-center justify-center text-white transition-all ${
                        isCompleted ? 'bg-green-500 shadow-lg' :
                        isActive ? 'bg-blue-500 animate-pulse' :
                        'bg-gray-300'
                      }`}>
                        {stepStatus === 'running' ? (
                          <Loader2 className="w-8 h-8 animate-spin" />
                        ) : (
                          <step.icon className="w-8 h-8" />
                        )}
                      </div>
                      <p className={`text-xs mt-2 font-medium ${
                        isCompleted ? 'text-green-700' :
                        isActive ? 'text-blue-700' :
                        'text-gray-400'
                      }`}>
                        {step.name}
                      </p>
                      {pipelineSteps[index]?.duration && (
                        <p className="text-xs text-gray-500 mt-1">
                          {Math.round(pipelineSteps[index].duration!)}ms
                        </p>
                      )}
                    </div>
                    {index < pipelineFlow.length - 1 && (
                      <ArrowRight className={`w-8 h-8 mx-4 flex-shrink-0 ${
                        isCompleted ? 'text-green-500' :
                        isActive ? 'text-blue-500 animate-pulse' :
                        'text-gray-300'
                      }`} />
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Data Cleaning Comparison */}
      {result && result.beforeCleaning && result.afterCleaning && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Before Cleaning */}
          <div className="card border-2 border-red-200">
            <div className="flex items-center gap-2 mb-4">
              <AlertCircle className="w-5 h-5 text-red-600" />
              <h3 className="font-semibold text-red-800">Before Cleaning</h3>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Total Records</span>
                <span className="font-semibold">{result.beforeCleaning.totalRecords.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-red-700">
                <span className="text-sm">Invalid Records</span>
                <span className="font-semibold">{result.beforeCleaning.invalidRecords}</span>
              </div>
              <div className="flex justify-between text-red-700">
                <span className="text-sm">Duplicate Records</span>
                <span className="font-semibold">{result.beforeCleaning.duplicateRecords}</span>
              </div>
              <div className="flex justify-between text-red-700">
                <span className="text-sm">Missing Fields</span>
                <span className="font-semibold">{result.beforeCleaning.missingFields}</span>
              </div>
            </div>
          </div>

          {/* After Cleaning */}
          <div className="card border-2 border-green-200">
            <div className="flex items-center gap-2 mb-4">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <h3 className="font-semibold text-green-800">After Cleaning</h3>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Total Records</span>
                <span className="font-semibold">{result.afterCleaning.totalRecords.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-green-700">
                <span className="text-sm">Valid Records</span>
                <span className="font-semibold">{result.afterCleaning.validRecords.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-green-700">
                <span className="text-sm">Normalized Records</span>
                <span className="font-semibold">{result.afterCleaning.normalizedRecords.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-green-700">
                <span className="text-sm">Errors</span>
                <span className="font-semibold">{result.afterCleaning.errors}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Result Summary */}
      {result && (
        <div className="card bg-green-50 border-green-200">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle className="w-6 h-6 text-green-600" />
            <h3 className="font-semibold text-green-800">{result.message}</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(result.counts).map(([key, value]) => (
              <div key={key} className="bg-white rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-gray-900">{value as number}</p>
                <p className="text-sm text-gray-500 capitalize">{key.replace(/_/g, ' ')}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Supported Sources */}
      <div className="card">
        <h3 className="font-semibold mb-4">Supported Data Sources</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { name: 'FHIR R4', color: 'bg-blue-100 text-blue-700' },
            { name: 'HL7v2', color: 'bg-purple-100 text-purple-700' },
            { name: 'X12 EDI', color: 'bg-green-100 text-green-700' },
            { name: 'Apple HealthKit', color: 'bg-gray-100 text-gray-700' },
            { name: 'Google Fit', color: 'bg-red-100 text-red-700' },
            { name: 'Fitbit', color: 'bg-teal-100 text-teal-700' },
            { name: 'DICOM', color: 'bg-indigo-100 text-indigo-700' },
            { name: 'CDA/CCDA', color: 'bg-yellow-100 text-yellow-700' },
          ].map(source => (
            <div key={source.name} className={`px-3 py-2 rounded text-sm font-medium text-center ${source.color}`}>
              {source.name}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
