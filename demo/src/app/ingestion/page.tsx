'use client'

import { useState } from 'react'
import { Upload, Database, Play, CheckCircle, AlertCircle, Loader2 } from 'lucide-react'

export default function IngestionPage() {
  const [mode, setMode] = useState<'fhir' | 'synthetic'>('synthetic')
  const [isLoading, setIsLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [syntheticConfig, setSyntheticConfig] = useState({
    numPatients: 100,
    denialRate: 0.15,
  })

  const handleIngest = async () => {
    setIsLoading(true)
    setResult(null)

    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 3000))

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
    })

    setIsLoading(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Data Ingestion</h1>
        <p className="text-gray-500 mt-1">Import FHIR data or generate synthetic data for demos</p>
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
                Generating Data...
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

      {mode === 'fhir' && (
        <div className="card">
          <div className="border-2 border-dashed border-gray-200 rounded-lg p-12 text-center">
            <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="font-medium text-gray-900">Drop FHIR Bundle JSON here</h3>
            <p className="text-sm text-gray-500 mt-1">or click to browse</p>
            <input type="file" accept=".json" className="hidden" />
          </div>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="card bg-green-50 border-green-200">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle className="w-6 h-6 text-green-600" />
            <h3 className="font-semibold text-green-800">{result.message}</h3>
          </div>
          <div className="grid grid-cols-4 gap-4">
            {Object.entries(result.counts).map(([key, value]) => (
              <div key={key} className="bg-white rounded-lg p-3 text-center">
                <p className="text-2xl font-bold text-gray-900">{value as number}</p>
                <p className="text-sm text-gray-500 capitalize">{key}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
