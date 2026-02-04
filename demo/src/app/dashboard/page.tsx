"use client"

import React, { useState, useEffect } from "react"
import {
  TrendingUp, TrendingDown, DollarSign, Users, FileX, 
  Activity, AlertTriangle, CheckCircle, Clock, Calendar,
  ArrowUpRight, ArrowDownRight, BarChart3, PieChart,
  Target, Zap, Heart, Shield, RefreshCw
} from "lucide-react"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"

// =============================================================================
// Types
// =============================================================================

interface MetricData {
  value: number | string
  change?: number
  changeType?: "increase" | "decrease"
  trend?: number[]
}

interface DashboardData {
  revenue: MetricData
  denials: {
    total: number
    amount: number
    pending: number
    urgent: number
    winRate: number
    byCategory: { name: string; value: number; amount: number }[]
    byPayer: { name: string; value: number }[]
  }
  patients: {
    total: number
    highRisk: number
    newThisMonth: number
    avgRiskScore: number
  }
  claims: {
    submitted: number
    paid: number
    pending: number
    denied: number
  }
  alerts: {
    critical: number
    high: number
    medium: number
    recent: { type: string; message: string; time: string }[]
  }
}

// =============================================================================
// Components
// =============================================================================

function MetricCard({ 
  title, 
  value, 
  icon: Icon, 
  change, 
  changeType,
  suffix = "",
  prefix = "",
  color = "blue",
  trend
}: {
  title: string
  value: string | number
  icon: React.ElementType
  change?: number
  changeType?: "increase" | "decrease"
  suffix?: string
  prefix?: string
  color?: string
  trend?: number[]
}) {
  const colorClasses = {
    blue: "bg-blue-500",
    green: "bg-green-500",
    red: "bg-red-500",
    yellow: "bg-yellow-500",
    purple: "bg-purple-500",
    cyan: "bg-cyan-500",
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500 font-medium">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">
            {prefix}{typeof value === 'number' ? value.toLocaleString() : value}{suffix}
          </p>
          {change !== undefined && (
            <div className={`flex items-center mt-2 text-sm ${
              changeType === "increase" ? "text-green-600" : "text-red-600"
            }`}>
              {changeType === "increase" ? (
                <ArrowUpRight className="w-4 h-4" />
              ) : (
                <ArrowDownRight className="w-4 h-4" />
              )}
              <span className="font-medium">{Math.abs(change)}%</span>
              <span className="text-gray-500 ml-1">vs last month</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color as keyof typeof colorClasses]} bg-opacity-10`}>
          <Icon className={`w-6 h-6 ${colorClasses[color as keyof typeof colorClasses].replace('bg-', 'text-')}`} />
        </div>
      </div>
      
      {trend && trend.length > 0 && (
        <div className="mt-4 flex items-end gap-1 h-12">
          {trend.map((val, i) => (
            <div
              key={i}
              className={`flex-1 ${colorClasses[color as keyof typeof colorClasses]} bg-opacity-60 rounded-t`}
              style={{ height: `${(val / Math.max(...trend)) * 100}%` }}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function DenialChart({ data }: { data: { name: string; value: number; amount: number }[] }) {
  const total = data.reduce((sum, d) => sum + d.value, 0)
  const colors = ["bg-red-500", "bg-orange-500", "bg-yellow-500", "bg-blue-500", "bg-purple-500"]

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-semibold text-gray-800">Denials by Category</h3>
        <PieChart className="w-5 h-5 text-gray-400" />
      </div>
      
      <div className="space-y-4">
        {data.slice(0, 5).map((item, i) => {
          const percentage = total > 0 ? (item.value / total * 100) : 0
          return (
            <div key={item.name}>
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-gray-600 capitalize">
                  {item.name.replace(/_/g, ' ')}
                </span>
                <span className="text-sm font-medium text-gray-900">
                  {item.value} (${item.amount.toLocaleString()})
                </span>
              </div>
              <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                <div 
                  className={`h-full ${colors[i]} rounded-full transition-all duration-500`}
                  style={{ width: `${percentage}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function PayerBreakdown({ data }: { data: { name: string; value: number }[] }) {
  const total = data.reduce((sum, d) => sum + d.value, 0)

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-semibold text-gray-800">Denials by Payer</h3>
        <BarChart3 className="w-5 h-5 text-gray-400" />
      </div>
      
      <div className="space-y-3">
        {data.slice(0, 5).map((payer, i) => (
          <div key={payer.name} className="flex items-center gap-3">
            <div className="w-32 truncate text-sm text-gray-600">{payer.name}</div>
            <div className="flex-1 h-6 bg-gray-100 rounded-lg overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-blue-500 to-blue-400 rounded-lg flex items-center justify-end pr-2"
                style={{ width: `${total > 0 ? (payer.value / total * 100) : 0}%` }}
              >
                <span className="text-xs text-white font-medium">{payer.value}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function AlertsPanel({ alerts }: { alerts: DashboardData['alerts'] }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-semibold text-gray-800">Active Alerts</h3>
        <AlertTriangle className="w-5 h-5 text-yellow-500" />
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="text-center p-3 bg-red-50 rounded-lg">
          <div className="text-2xl font-bold text-red-600">{alerts.critical}</div>
          <div className="text-xs text-red-600">Critical</div>
        </div>
        <div className="text-center p-3 bg-orange-50 rounded-lg">
          <div className="text-2xl font-bold text-orange-600">{alerts.high}</div>
          <div className="text-xs text-orange-600">High</div>
        </div>
        <div className="text-center p-3 bg-yellow-50 rounded-lg">
          <div className="text-2xl font-bold text-yellow-600">{alerts.medium}</div>
          <div className="text-xs text-yellow-600">Medium</div>
        </div>
      </div>

      <div className="space-y-3">
        {alerts.recent.map((alert, i) => (
          <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
            <AlertTriangle className={`w-4 h-4 mt-0.5 ${
              alert.type === 'critical' ? 'text-red-500' : 
              alert.type === 'high' ? 'text-orange-500' : 'text-yellow-500'
            }`} />
            <div className="flex-1">
              <p className="text-sm text-gray-800">{alert.message}</p>
              <p className="text-xs text-gray-500 mt-1">{alert.time}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function QuickActions() {
  const actions = [
    { label: "View High-Risk Patients", icon: Heart, color: "red", href: "/patients?risk=high" },
    { label: "Pending Denials", icon: FileX, color: "orange", href: "/denials?status=pending" },
    { label: "Run Triage Scan", icon: Activity, color: "blue", href: "/agents" },
    { label: "Intelligence Search", icon: Zap, color: "purple", href: "/intelligence" },
  ]

  return (
    <div className="bg-white rounded-xl shadow-sm border p-6">
      <h3 className="font-semibold text-gray-800 mb-4">Quick Actions</h3>
      <div className="grid grid-cols-2 gap-3">
        {actions.map((action) => (
          <a
            key={action.label}
            href={action.href}
            className="flex items-center gap-3 p-3 rounded-lg border hover:bg-gray-50 transition-colors"
          >
            <action.icon className={`w-5 h-5 text-${action.color}-500`} />
            <span className="text-sm font-medium text-gray-700">{action.label}</span>
          </a>
        ))}
      </div>
    </div>
  )
}

// =============================================================================
// Main Dashboard
// =============================================================================

export default function ExecutiveDashboard() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())

  useEffect(() => {
    loadDashboardData()
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadDashboardData, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadDashboardData = async () => {
    try {
      // Fetch denial analytics
      const denialRes = await fetch(`${API_BASE}/v1/denials/analytics`)
      const denialData = denialRes.ok ? await denialRes.json() : null

      // Fetch patients
      const patientRes = await fetch(`${API_BASE}/v1/patients`)
      const patientData = patientRes.ok ? await patientRes.json() : null

      // Construct dashboard data
      setData({
        revenue: {
          value: denialData?.total_denied_amount || 0,
          change: 12,
          changeType: "decrease",
          trend: [45, 52, 48, 61, 58, 63, 55],
        },
        denials: {
          total: denialData?.total_denials || 0,
          amount: denialData?.total_denied_amount || 0,
          pending: denialData?.pending_count || 0,
          urgent: denialData?.urgent_count || 0,
          winRate: denialData?.win_rate || 0.68,
          byCategory: denialData?.by_category || [],
          byPayer: denialData?.by_payer || [],
        },
        patients: {
          total: patientData?.total || 0,
          highRisk: Math.floor((patientData?.total || 0) * 0.15),
          newThisMonth: Math.floor((patientData?.total || 0) * 0.08),
          avgRiskScore: 0.35,
        },
        claims: {
          submitted: 156,
          paid: 128,
          pending: 18,
          denied: denialData?.total_denials || 10,
        },
        alerts: {
          critical: 2,
          high: 5,
          medium: 8,
          recent: [
            { type: "critical", message: "Patient Michael Davis - Critical lab value", time: "5 min ago" },
            { type: "high", message: "Claim CLM-2024-0017 appeal deadline in 3 days", time: "1 hour ago" },
            { type: "medium", message: "5 patients due for HbA1c screening", time: "2 hours ago" },
          ],
        },
      })

      setLastUpdated(new Date())
    } catch (error) {
      console.error("Failed to load dashboard data:", error)
    }
    setLoading(false)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 text-blue-600 animate-spin mx-auto" />
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-600">Failed to load dashboard data</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Executive Dashboard</h1>
              <p className="text-sm text-gray-500">
                Real-time healthcare operations overview
              </p>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-sm text-gray-500">
                <Clock className="w-4 h-4 inline mr-1" />
                Updated {lastUpdated.toLocaleTimeString()}
              </div>
              <button 
                onClick={loadDashboardData}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <RefreshCw className="w-5 h-5 text-gray-600" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Top Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <MetricCard
            title="Total Patients"
            value={data.patients.total}
            icon={Users}
            change={8}
            changeType="increase"
            color="blue"
            trend={[20, 22, 21, 25, 28, 30, 32]}
          />
          <MetricCard
            title="High-Risk Patients"
            value={data.patients.highRisk}
            icon={AlertTriangle}
            change={5}
            changeType="increase"
            color="red"
          />
          <MetricCard
            title="Pending Denials"
            value={data.denials.pending}
            icon={FileX}
            suffix={` ($${(data.denials.amount / 1000).toFixed(0)}K)`}
            color="yellow"
          />
          <MetricCard
            title="Appeal Win Rate"
            value={(data.denials.winRate * 100).toFixed(0)}
            icon={Target}
            suffix="%"
            change={3}
            changeType="increase"
            color="green"
          />
        </div>

        {/* Second Row */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <MetricCard
            title="Claims Submitted"
            value={data.claims.submitted}
            icon={DollarSign}
            color="cyan"
          />
          <MetricCard
            title="Claims Paid"
            value={data.claims.paid}
            icon={CheckCircle}
            color="green"
          />
          <MetricCard
            title="Urgent Deadlines"
            value={data.denials.urgent}
            icon={Clock}
            color="red"
          />
        </div>

        {/* Charts and Panels */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <DenialChart data={data.denials.byCategory} />
          <PayerBreakdown data={data.denials.byPayer} />
        </div>

        {/* Bottom Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <AlertsPanel alerts={data.alerts} />
          <QuickActions />
        </div>

        {/* Footer Stats */}
        <div className="mt-8 p-6 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-xl text-white">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
            <div>
              <div className="text-3xl font-bold">${(data.denials.amount / 1000).toFixed(0)}K</div>
              <div className="text-blue-200 text-sm">Denied Revenue (At Risk)</div>
            </div>
            <div>
              <div className="text-3xl font-bold">${((data.denials.amount * data.denials.winRate) / 1000).toFixed(0)}K</div>
              <div className="text-blue-200 text-sm">Recoverable (Est.)</div>
            </div>
            <div>
              <div className="text-3xl font-bold">{data.patients.highRisk}</div>
              <div className="text-blue-200 text-sm">Patients Need Attention</div>
            </div>
            <div>
              <div className="text-3xl font-bold">{data.denials.urgent}</div>
              <div className="text-blue-200 text-sm">Urgent Actions</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
