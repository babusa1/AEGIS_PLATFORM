'use client'

import { useState } from 'react'
import { 
  Activity, 
  DollarSign, 
  Users, 
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  Bot,
  FileText
} from 'lucide-react'
import { MetricCard } from '@/components/dashboard/MetricCard'
import { DenialChart } from '@/components/dashboard/DenialChart'
import { RecentAlerts } from '@/components/dashboard/RecentAlerts'
import { AgentActivity } from '@/components/dashboard/AgentActivity'
import { QuickActions } from '@/components/dashboard/QuickActions'

export default function Dashboard() {
  const [timeRange, setTimeRange] = useState('30d')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500 mt-1">Healthcare operations overview</p>
        </div>
        <select 
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          className="px-4 py-2 bg-white border border-gray-200 rounded-lg text-sm"
        >
          <option value="7d">Last 7 days</option>
          <option value="30d">Last 30 days</option>
          <option value="90d">Last 90 days</option>
        </select>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Claims"
          value="12,847"
          change={+5.2}
          icon={FileText}
          color="blue"
        />
        <MetricCard
          title="Denial Rate"
          value="14.2%"
          change={-2.1}
          icon={AlertTriangle}
          color="red"
          invertChange
        />
        <MetricCard
          title="Revenue at Risk"
          value="$2.4M"
          change={-8.5}
          icon={DollarSign}
          color="yellow"
          invertChange
        />
        <MetricCard
          title="Appeals Won"
          value="68%"
          change={+12.3}
          icon={TrendingUp}
          color="green"
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Denial Trends Chart */}
        <div className="lg:col-span-2 card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Denial Trends</h2>
            <div className="flex gap-2">
              <span className="badge badge-info">By Category</span>
            </div>
          </div>
          <DenialChart />
        </div>

        {/* Quick Actions */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <QuickActions />
        </div>
      </div>

      {/* Bottom Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Alerts */}
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Recent Alerts</h2>
            <button className="text-aegis-primary text-sm hover:underline">View all</button>
          </div>
          <RecentAlerts />
        </div>

        {/* Agent Activity */}
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-gray-900">
              <Bot className="inline w-5 h-5 mr-2" />
              Agent Activity
            </h2>
            <span className="badge badge-success">3 Active</span>
          </div>
          <AgentActivity />
        </div>
      </div>
    </div>
  )
}
