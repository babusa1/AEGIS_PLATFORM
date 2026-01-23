'use client'

import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Legend
} from 'recharts'

const data = [
  { month: 'Jul', medical_necessity: 45, authorization: 32, coding: 28, documentation: 15 },
  { month: 'Aug', medical_necessity: 52, authorization: 38, coding: 25, documentation: 18 },
  { month: 'Sep', medical_necessity: 48, authorization: 42, coding: 30, documentation: 12 },
  { month: 'Oct', medical_necessity: 55, authorization: 35, coding: 32, documentation: 20 },
  { month: 'Nov', medical_necessity: 42, authorization: 40, coding: 28, documentation: 16 },
  { month: 'Dec', medical_necessity: 38, authorization: 36, coding: 24, documentation: 14 },
]

export function DenialChart() {
  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="medicalNecessity" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#EF4444" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#EF4444" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="authorization" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#F59E0B" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#F59E0B" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="coding" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0066CC" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#0066CC" stopOpacity={0}/>
            </linearGradient>
            <linearGradient id="documentation" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis dataKey="month" stroke="#9CA3AF" fontSize={12} />
          <YAxis stroke="#9CA3AF" fontSize={12} />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: 'white', 
              border: '1px solid #E5E7EB',
              borderRadius: '8px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }}
          />
          <Legend />
          <Area 
            type="monotone" 
            dataKey="medical_necessity" 
            name="Medical Necessity"
            stroke="#EF4444" 
            fillOpacity={1} 
            fill="url(#medicalNecessity)" 
          />
          <Area 
            type="monotone" 
            dataKey="authorization" 
            name="Authorization"
            stroke="#F59E0B" 
            fillOpacity={1} 
            fill="url(#authorization)" 
          />
          <Area 
            type="monotone" 
            dataKey="coding" 
            name="Coding"
            stroke="#0066CC" 
            fillOpacity={1} 
            fill="url(#coding)" 
          />
          <Area 
            type="monotone" 
            dataKey="documentation" 
            name="Documentation"
            stroke="#10B981" 
            fillOpacity={1} 
            fill="url(#documentation)" 
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
