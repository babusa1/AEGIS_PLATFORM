"use client"

import React, { useState } from "react"
import { 
  Search, Shield, Brain, FileText, Upload, AlertTriangle, 
  CheckCircle, XCircle, Loader2, Eye, EyeOff, Sparkles,
  TrendingUp, TrendingDown, AlertCircle, FileUp
} from "lucide-react"

// API base URL
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"

// =============================================================================
// Type Definitions
// =============================================================================

interface PHIMatch {
  type: string
  text: string
  start: number
  end: number
  confidence: number
}

interface DenialPrediction {
  claim_id: string
  denial_probability: number
  risk_level: string
  primary_reason: string | null
  recommendations: string[]
  key_factors: { factor: string; impact_pct: string }[]
}

interface RAGResult {
  id: string
  content: string
  score: number
  title: string
  source: string
}

// =============================================================================
// PHI Detection Component
// =============================================================================

function PHIDetector() {
  const [text, setText] = useState(
    "Patient John Smith (DOB: 01/15/1980, SSN: 123-45-6789) was seen at 123 Main Street. " +
    "Contact: john.smith@email.com, Phone: (555) 123-4567. MRN: ABC123456"
  )
  const [matches, setMatches] = useState<PHIMatch[]>([])
  const [redactedText, setRedactedText] = useState("")
  const [loading, setLoading] = useState(false)
  const [showRedacted, setShowRedacted] = useState(false)

  const detectPHI = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/v1/security/phi/detect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, sensitivity: "high" }),
      })
      const data = await res.json()
      setMatches(data.matches || [])
    } catch (error) {
      console.error("Detection failed:", error)
    }
    setLoading(false)
  }

  const redactPHI = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/v1/security/phi/redact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, strategy: "mask", sensitivity: "high" }),
      })
      const data = await res.json()
      setRedactedText(data.redacted_text || "")
      setShowRedacted(true)
    } catch (error) {
      console.error("Redaction failed:", error)
    }
    setLoading(false)
  }

  const highlightPHI = (text: string, matches: PHIMatch[]) => {
    if (!matches.length) return text
    
    let result = []
    let lastEnd = 0
    
    const sortedMatches = [...matches].sort((a, b) => a.start - b.start)
    
    for (const match of sortedMatches) {
      if (match.start > lastEnd) {
        result.push(text.slice(lastEnd, match.start))
      }
      result.push(
        <span 
          key={match.start} 
          className="bg-red-200 text-red-800 px-1 rounded cursor-help"
          title={`${match.type} (${(match.confidence * 100).toFixed(0)}% confidence)`}
        >
          {text.slice(match.start, match.end)}
        </span>
      )
      lastEnd = match.end
    }
    
    if (lastEnd < text.length) {
      result.push(text.slice(lastEnd))
    }
    
    return result
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-red-100 rounded-lg">
          <Shield className="h-6 w-6 text-red-600" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-gray-800">PHI Detection & Redaction</h2>
          <p className="text-sm text-gray-500">HIPAA-compliant PHI masking</p>
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Input Text (with PHI)
          </label>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="w-full h-32 p-3 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            placeholder="Enter text containing PHI..."
          />
        </div>

        <div className="flex gap-3">
          <button
            onClick={detectPHI}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />}
            Detect PHI
          </button>
          <button
            onClick={redactPHI}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <EyeOff className="h-4 w-4" />}
            Redact PHI
          </button>
        </div>

        {matches.length > 0 && (
          <div className="p-4 bg-red-50 rounded-lg">
            <h3 className="font-medium text-red-800 mb-2">
              Detected {matches.length} PHI Element(s):
            </h3>
            <div className="text-sm text-gray-700 leading-relaxed">
              {highlightPHI(text, matches)}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              {[...new Set(matches.map(m => m.type))].map(type => (
                <span 
                  key={type}
                  className="px-2 py-1 bg-red-200 text-red-800 text-xs rounded-full"
                >
                  {type.toUpperCase()}
                </span>
              ))}
            </div>
          </div>
        )}

        {showRedacted && redactedText && (
          <div className="p-4 bg-green-50 rounded-lg">
            <h3 className="font-medium text-green-800 mb-2">Redacted Output:</h3>
            <p className="text-sm text-gray-700 font-mono">{redactedText}</p>
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Denial Prediction Component
// =============================================================================

function DenialPredictor() {
  const [prediction, setPrediction] = useState<DenialPrediction | null>(null)
  const [loading, setLoading] = useState(false)

  const sampleClaim = {
    id: "CLM-2024-001",
    claim_type: "professional",
    place_of_service: "11",
    diagnoses: ["M54.5", "G89.29"],
    lines: [
      { cpt: "99215", charge: 250 },
      { cpt: "97110", charge: 75 },
      { cpt: "97140", charge: 60 },
    ],
    provider_npi: "1234567890",
    provider_specialty: "orthopedic",
    in_network: true,
    payer_type: "commercial",
    payer_id: "BCBS001",
    has_prior_auth: false,
    service_date: "2024-01-15",
  }

  const predictDenial = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/v1/ml/predict/denial`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ claim: sampleClaim }),
      })
      const data = await res.json()
      setPrediction(data)
    } catch (error) {
      console.error("Prediction failed:", error)
    }
    setLoading(false)
  }

  const getRiskColor = (level: string) => {
    switch (level) {
      case "critical": return "bg-red-600"
      case "high": return "bg-orange-500"
      case "medium": return "bg-yellow-500"
      default: return "bg-green-500"
    }
  }

  const getRiskIcon = (level: string) => {
    switch (level) {
      case "critical":
      case "high":
        return <TrendingUp className="h-5 w-5 text-white" />
      default:
        return <TrendingDown className="h-5 w-5 text-white" />
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-purple-100 rounded-lg">
          <Brain className="h-6 w-6 text-purple-600" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-gray-800">Denial Prediction</h2>
          <p className="text-sm text-gray-500">ML-powered claim risk scoring</p>
        </div>
      </div>

      <div className="space-y-4">
        <div className="p-4 bg-gray-50 rounded-lg">
          <h3 className="font-medium text-gray-700 mb-2">Sample Claim</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div><span className="text-gray-500">Claim ID:</span> {sampleClaim.id}</div>
            <div><span className="text-gray-500">Total Charge:</span> ${sampleClaim.lines.reduce((sum, l) => sum + l.charge, 0)}</div>
            <div><span className="text-gray-500">Diagnoses:</span> {sampleClaim.diagnoses.join(", ")}</div>
            <div><span className="text-gray-500">CPT Codes:</span> {sampleClaim.lines.map(l => l.cpt).join(", ")}</div>
            <div><span className="text-gray-500">Prior Auth:</span> {sampleClaim.has_prior_auth ? "Yes" : "No"}</div>
            <div><span className="text-gray-500">In Network:</span> {sampleClaim.in_network ? "Yes" : "No"}</div>
          </div>
        </div>

        <button
          onClick={predictDenial}
          disabled={loading}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
        >
          {loading ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Sparkles className="h-5 w-5" />
          )}
          Predict Denial Risk
        </button>

        {prediction && (
          <div className="space-y-4">
            {/* Risk Score */}
            <div className={`p-4 rounded-lg ${getRiskColor(prediction.risk_level)} text-white`}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-sm opacity-80">Denial Probability</div>
                  <div className="text-3xl font-bold">
                    {(prediction.denial_probability * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {getRiskIcon(prediction.risk_level)}
                  <span className="text-xl font-semibold uppercase">
                    {prediction.risk_level}
                  </span>
                </div>
              </div>
            </div>

            {/* Primary Reason */}
            {prediction.primary_reason && (
              <div className="p-4 bg-orange-50 rounded-lg">
                <div className="flex items-center gap-2 text-orange-800">
                  <AlertTriangle className="h-5 w-5" />
                  <span className="font-medium">Primary Risk: {prediction.primary_reason.replace(/_/g, " ").toUpperCase()}</span>
                </div>
              </div>
            )}

            {/* Key Factors */}
            {prediction.key_factors?.length > 0 && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <h4 className="font-medium text-gray-700 mb-3">Key Risk Factors</h4>
                <div className="space-y-2">
                  {prediction.key_factors.map((factor, i) => (
                    <div key={i} className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">{factor.factor}</span>
                      <span className="text-sm font-medium text-red-600">{factor.impact_pct}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {prediction.recommendations?.length > 0 && (
              <div className="p-4 bg-blue-50 rounded-lg">
                <h4 className="font-medium text-blue-800 mb-3">Recommendations</h4>
                <ul className="space-y-2">
                  {prediction.recommendations.map((rec, i) => (
                    <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                      <CheckCircle className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// RAG Search Component
// =============================================================================

function RAGSearch() {
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<RAGResult[]>([])
  const [answer, setAnswer] = useState("")
  const [loading, setLoading] = useState(false)
  const [ingesting, setIngesting] = useState(false)

  const sampleDocs = [
    "Medicare covers physical therapy when ordered by a physician and the service is medically necessary. Prior authorization is required for extended therapy beyond 30 sessions.",
    "HIPAA requires covered entities to implement safeguards to protect PHI. Business associates must also comply with HIPAA security rules.",
    "Claims must be submitted within 90 days of service date for most commercial payers. Medicare allows up to 12 months for timely filing.",
  ]

  const ingestSampleDocs = async () => {
    setIngesting(true)
    for (const doc of sampleDocs) {
      try {
        await fetch(`${API_BASE}/v1/rag/ingest/text`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            text: doc, 
            title: "Policy Document",
            source: "sample_policy"
          }),
        })
      } catch (error) {
        console.error("Ingestion failed:", error)
      }
    }
    setIngesting(false)
    alert("Sample documents ingested!")
  }

  const search = async () => {
    if (!query.trim()) return
    
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/v1/rag/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: 3 }),
      })
      const data = await res.json()
      setResults(data.citations || [])
      setAnswer(data.answer || "")
    } catch (error) {
      console.error("Search failed:", error)
    }
    setLoading(false)
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-3 bg-blue-100 rounded-lg">
          <Search className="h-6 w-6 text-blue-600" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-gray-800">RAG Knowledge Search</h2>
          <p className="text-sm text-gray-500">Search clinical documents & policies</p>
        </div>
      </div>

      <div className="space-y-4">
        <button
          onClick={ingestSampleDocs}
          disabled={ingesting}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
        >
          {ingesting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <FileUp className="h-4 w-4" />
          )}
          Load Sample Policies
        </button>

        <div className="flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && search()}
            placeholder="Ask about policies, guidelines..."
            className="flex-1 px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={search}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Search className="h-5 w-5" />}
          </button>
        </div>

        {answer && (
          <div className="p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-800 mb-2">Answer</h4>
            <p className="text-sm text-gray-700">{answer}</p>
          </div>
        )}

        {results.length > 0 && (
          <div className="space-y-3">
            <h4 className="font-medium text-gray-700">Sources</h4>
            {results.map((result, i) => (
              <div key={i} className="p-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-2 mb-1">
                  <FileText className="h-4 w-4 text-gray-400" />
                  <span className="text-sm font-medium text-gray-700">
                    [{result.rank}] {result.document_title || "Document"}
                  </span>
                  <span className="text-xs text-gray-400">
                    ({(result.score * 100).toFixed(0)}% match)
                  </span>
                </div>
                <p className="text-sm text-gray-600 line-clamp-2">{result.excerpt}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// =============================================================================
// Main Page
// =============================================================================

export default function IntelligencePage() {
  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="max-w-7xl mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">
            AEGIS Healthcare Intelligence
          </h1>
          <p className="mt-2 text-gray-600">
            RAG Search | PHI Detection | Denial Prediction
          </p>
        </div>

        {/* Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* RAG Search - Full width on mobile, left column on desktop */}
          <div className="lg:col-span-1">
            <RAGSearch />
          </div>

          {/* PHI Detector */}
          <div className="lg:col-span-1">
            <PHIDetector />
          </div>

          {/* Denial Prediction - Full width */}
          <div className="lg:col-span-2">
            <DenialPredictor />
          </div>
        </div>

        {/* Feature Summary */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white rounded-lg p-4 shadow">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded">
                <Search className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <div className="font-medium text-gray-800">RAG Pipeline</div>
                <div className="text-sm text-gray-500">Semantic document search</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg p-4 shadow">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-red-100 rounded">
                <Shield className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <div className="font-medium text-gray-800">PHI Detection</div>
                <div className="text-sm text-gray-500">HIPAA 18 identifiers</div>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg p-4 shadow">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-purple-100 rounded">
                <Brain className="h-5 w-5 text-purple-600" />
              </div>
              <div>
                <div className="font-medium text-gray-800">Denial Prediction</div>
                <div className="text-sm text-gray-500">Pre-submission risk scoring</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
