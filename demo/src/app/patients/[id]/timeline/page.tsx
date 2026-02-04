"use client"

import React, { useState, useEffect } from "react"
import { useParams } from "next/navigation"
import { 
  Calendar, Activity, Pill, Stethoscope, FileText, 
  AlertTriangle, DollarSign, Heart, Clock, ChevronDown,
  ChevronUp, ArrowLeft, Filter, Search
} from "lucide-react"
import Link from "next/link"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"

// Event type definitions
type EventType = "encounter" | "condition" | "medication" | "claim" | "lab" | "vital" | "alert"

interface TimelineEvent {
  id: string
  type: EventType
  date: string
  title: string
  description: string
  details?: Record<string, any>
  severity?: "normal" | "warning" | "critical"
}

interface Patient {
  id: string
  given_name: string
  family_name: string
  mrn: string
  birth_date: string
}

// Event icon mapping
const eventIcons: Record<EventType, React.ReactNode> = {
  encounter: <Stethoscope className="w-4 h-4" />,
  condition: <Heart className="w-4 h-4" />,
  medication: <Pill className="w-4 h-4" />,
  claim: <DollarSign className="w-4 h-4" />,
  lab: <Activity className="w-4 h-4" />,
  vital: <Activity className="w-4 h-4" />,
  alert: <AlertTriangle className="w-4 h-4" />,
}

// Event color mapping
const eventColors: Record<EventType, string> = {
  encounter: "bg-blue-500",
  condition: "bg-red-500",
  medication: "bg-green-500",
  claim: "bg-yellow-500",
  lab: "bg-purple-500",
  vital: "bg-cyan-500",
  alert: "bg-orange-500",
}

const eventBgColors: Record<EventType, string> = {
  encounter: "bg-blue-50 border-blue-200",
  condition: "bg-red-50 border-red-200",
  medication: "bg-green-50 border-green-200",
  claim: "bg-yellow-50 border-yellow-200",
  lab: "bg-purple-50 border-purple-200",
  vital: "bg-cyan-50 border-cyan-200",
  alert: "bg-orange-50 border-orange-200",
}

function TimelineEventCard({ event, expanded, onToggle }: { 
  event: TimelineEvent
  expanded: boolean
  onToggle: () => void 
}) {
  const severityBorder = event.severity === "critical" 
    ? "border-l-4 border-l-red-500" 
    : event.severity === "warning"
    ? "border-l-4 border-l-yellow-500"
    : ""

  return (
    <div className={`relative pl-8 pb-8 last:pb-0`}>
      {/* Timeline line */}
      <div className="absolute left-[11px] top-6 bottom-0 w-0.5 bg-gray-200 last:hidden" />
      
      {/* Event dot */}
      <div className={`absolute left-0 top-1 w-6 h-6 rounded-full ${eventColors[event.type]} flex items-center justify-center text-white`}>
        {eventIcons[event.type]}
      </div>

      {/* Event card */}
      <div className={`ml-4 p-4 rounded-lg border ${eventBgColors[event.type]} ${severityBorder} cursor-pointer transition-all hover:shadow-md`}
        onClick={onToggle}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 text-xs text-gray-500 mb-1">
              <Clock className="w-3 h-3" />
              <span>{new Date(event.date).toLocaleDateString('en-US', { 
                weekday: 'short',
                year: 'numeric', 
                month: 'short', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
              })}</span>
              <span className="px-2 py-0.5 rounded-full bg-white text-xs font-medium capitalize">
                {event.type}
              </span>
              {event.severity === "critical" && (
                <span className="px-2 py-0.5 rounded-full bg-red-500 text-white text-xs font-medium">
                  Critical
                </span>
              )}
            </div>
            <h3 className="font-semibold text-gray-800">{event.title}</h3>
            <p className="text-sm text-gray-600 mt-1">{event.description}</p>
          </div>
          <button className="p-1 hover:bg-white/50 rounded">
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>

        {/* Expanded details */}
        {expanded && event.details && (
          <div className="mt-4 pt-4 border-t border-gray-200/50">
            <div className="grid grid-cols-2 gap-3 text-sm">
              {Object.entries(event.details).map(([key, value]) => (
                <div key={key}>
                  <span className="text-gray-500 capitalize">{key.replace(/_/g, ' ')}:</span>
                  <span className="ml-2 font-medium text-gray-800">
                    {typeof value === 'number' && key.includes('amount') 
                      ? `$${value.toLocaleString()}`
                      : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function PatientTimelinePage() {
  const params = useParams()
  const patientId = params.id as string

  const [patient, setPatient] = useState<Patient | null>(null)
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [filterTypes, setFilterTypes] = useState<Set<EventType>>(new Set())
  const [searchTerm, setSearchTerm] = useState("")

  useEffect(() => {
    loadPatientTimeline()
  }, [patientId])

  const loadPatientTimeline = async () => {
    setLoading(true)
    try {
      // Fetch patient 360 data
      const response = await fetch(`${API_BASE}/v1/patients/${patientId}`)
      if (!response.ok) throw new Error("Failed to load patient")
      
      const data = await response.json()
      
      setPatient(data.patient)
      
      // Convert data to timeline events
      const timelineEvents: TimelineEvent[] = []

      // Add encounters
      data.encounters?.forEach((enc: any) => {
        timelineEvents.push({
          id: `enc-${enc.id}`,
          type: "encounter",
          date: enc.admit_date,
          title: `${enc.type} Encounter`,
          description: enc.status === "finished" 
            ? `Completed at ${enc.facility || 'Healthcare Facility'}`
            : `${enc.status} encounter`,
          details: {
            facility: enc.facility,
            status: enc.status,
            discharge: enc.discharge_date,
          },
        })
      })

      // Add conditions
      data.conditions?.forEach((cond: any) => {
        timelineEvents.push({
          id: `cond-${cond.id}`,
          type: "condition",
          date: cond.onset_date || data.patient.created_at || new Date().toISOString(),
          title: cond.display,
          description: `Diagnosis: ${cond.code}`,
          details: {
            code: cond.code,
            status: cond.status,
          },
          severity: cond.status === "active" ? "warning" : "normal",
        })
      })

      // Add medications
      data.medications?.forEach((med: any) => {
        timelineEvents.push({
          id: `med-${med.id}`,
          type: "medication",
          date: med.start_date || new Date().toISOString(),
          title: med.display,
          description: `${med.dosage || ''} ${med.frequency || ''}`.trim(),
          details: {
            dosage: med.dosage,
            frequency: med.frequency,
            status: med.status,
          },
        })
      })

      // Add claims
      data.claims?.forEach((claim: any) => {
        const isDenied = claim.status === "denied"
        timelineEvents.push({
          id: `claim-${claim.id}`,
          type: "claim",
          date: claim.service_date || claim.created_at || new Date().toISOString(),
          title: `Claim ${claim.claim_number}`,
          description: isDenied 
            ? `Denied: ${claim.denial_reason || 'No reason provided'}`
            : `${claim.status}: $${claim.billed_amount?.toLocaleString() || 0}`,
          details: {
            claim_number: claim.claim_number,
            type: claim.type,
            status: claim.status,
            billed_amount: claim.billed_amount,
            paid_amount: claim.paid_amount,
          },
          severity: isDenied ? "critical" : "normal",
        })
      })

      // Add vitals (if available)
      data.vitals?.forEach((vital: any, index: number) => {
        timelineEvents.push({
          id: `vital-${index}`,
          type: "vital",
          date: vital.timestamp || new Date().toISOString(),
          title: `${vital.type?.replace(/_/g, ' ')} Reading`,
          description: `${vital.value} ${vital.unit}`,
          details: {
            type: vital.type,
            value: vital.value,
            unit: vital.unit,
          },
        })
      })

      // Sort by date (most recent first)
      timelineEvents.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
      
      setEvents(timelineEvents)
    } catch (error) {
      console.error("Failed to load timeline:", error)
    }
    setLoading(false)
  }

  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedIds)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedIds(newExpanded)
  }

  const toggleFilter = (type: EventType) => {
    const newFilters = new Set(filterTypes)
    if (newFilters.has(type)) {
      newFilters.delete(type)
    } else {
      newFilters.add(type)
    }
    setFilterTypes(newFilters)
  }

  // Filter events
  const filteredEvents = events.filter(event => {
    if (filterTypes.size > 0 && !filterTypes.has(event.type)) return false
    if (searchTerm) {
      const search = searchTerm.toLowerCase()
      return event.title.toLowerCase().includes(search) || 
             event.description.toLowerCase().includes(search)
    }
    return true
  })

  // Group events by month
  const groupedEvents = filteredEvents.reduce((groups, event) => {
    const date = new Date(event.date)
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
    if (!groups[key]) groups[key] = []
    groups[key].push(event)
    return groups
  }, {} as Record<string, TimelineEvent[]>)

  const eventTypes: EventType[] = ["encounter", "condition", "medication", "claim", "lab", "vital"]

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-4">
          <div className="flex items-center gap-4 mb-4">
            <Link 
              href={`/patients/${patientId}`}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">
                Patient Timeline
              </h1>
              {patient && (
                <p className="text-gray-600">
                  {patient.given_name} {patient.family_name} • MRN: {patient.mrn}
                </p>
              )}
            </div>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-xs">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search events..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-gray-500" />
              {eventTypes.map(type => (
                <button
                  key={type}
                  onClick={() => toggleFilter(type)}
                  className={`flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                    filterTypes.size === 0 || filterTypes.has(type)
                      ? `${eventColors[type]} text-white`
                      : "bg-gray-200 text-gray-600"
                  }`}
                >
                  {eventIcons[type]}
                  <span className="capitalize">{type}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="max-w-5xl mx-auto px-4 py-8">
        {Object.entries(groupedEvents).length === 0 ? (
          <div className="text-center py-12 text-gray-500">
            <Calendar className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No events found</p>
          </div>
        ) : (
          Object.entries(groupedEvents).map(([monthKey, monthEvents]) => {
            const [year, month] = monthKey.split('-')
            const monthName = new Date(parseInt(year), parseInt(month) - 1).toLocaleString('default', { 
              month: 'long', 
              year: 'numeric' 
            })

            return (
              <div key={monthKey} className="mb-8">
                <div className="flex items-center gap-3 mb-4">
                  <Calendar className="w-5 h-5 text-blue-600" />
                  <h2 className="text-lg font-semibold text-gray-800">{monthName}</h2>
                  <span className="px-2 py-0.5 bg-gray-200 rounded-full text-xs text-gray-600">
                    {monthEvents.length} events
                  </span>
                </div>

                <div className="ml-2">
                  {monthEvents.map(event => (
                    <TimelineEventCard
                      key={event.id}
                      event={event}
                      expanded={expandedIds.has(event.id)}
                      onToggle={() => toggleExpanded(event.id)}
                    />
                  ))}
                </div>
              </div>
            )
          })
        )}

        {/* Summary stats */}
        <div className="mt-8 p-6 bg-white rounded-xl border">
          <h3 className="font-semibold text-gray-800 mb-4">Timeline Summary</h3>
          <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
            {eventTypes.map(type => {
              const count = events.filter(e => e.type === type).length
              return (
                <div key={type} className="text-center">
                  <div className={`w-10 h-10 mx-auto mb-2 rounded-full ${eventColors[type]} flex items-center justify-center text-white`}>
                    {eventIcons[type]}
                  </div>
                  <div className="text-2xl font-bold text-gray-800">{count}</div>
                  <div className="text-xs text-gray-500 capitalize">{type}s</div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
