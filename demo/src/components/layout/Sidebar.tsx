'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { 
  LayoutDashboard, 
  Users, 
  FileText, 
  AlertCircle, 
  Bot, 
  BarChart3,
  Settings,
  Database,
  Shield,
  MessageSquare
} from 'lucide-react'
import clsx from 'clsx'

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Cowork', href: '/cowork', icon: MessageSquare },
  { name: 'Patients', href: '/patients', icon: Users },
  { name: 'Claims', href: '/claims', icon: FileText },
  { name: 'Denials', href: '/denials', icon: AlertCircle },
  { name: 'AI Agents', href: '/agents', icon: Bot },
  { name: 'Analytics', href: '/intelligence', icon: BarChart3 },
  { name: 'Data Moat', href: '/data-moat', icon: Database },
  { name: 'Data Ingestion', href: '/ingestion', icon: Database },
]

const bottomNav = [
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <div className="w-64 bg-aegis-dark text-white flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-aegis-primary to-aegis-accent rounded-lg flex items-center justify-center">
            <Shield className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold">VeritOS</h1>
            <p className="text-xs text-gray-400">Healthcare Intelligence</p>
          </div>
        </div>
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navigation.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.name}
              href={item.href}
              className={clsx(
                'flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200',
                isActive 
                  ? 'bg-aegis-primary text-white' 
                  : 'text-gray-300 hover:bg-white/10 hover:text-white'
              )}
            >
              <item.icon className="w-5 h-5" />
              <span className="font-medium">{item.name}</span>
              {item.name === 'Denials' && (
                <span className="ml-auto bg-red-500 text-white text-xs px-2 py-0.5 rounded-full">
                  23
                </span>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Bottom Navigation */}
      <div className="p-4 border-t border-white/10">
        {bottomNav.map((item) => (
          <Link
            key={item.name}
            href={item.href}
            className="flex items-center gap-3 px-4 py-3 rounded-lg text-gray-300 hover:bg-white/10 hover:text-white transition-all duration-200"
          >
            <item.icon className="w-5 h-5" />
            <span className="font-medium">{item.name}</span>
          </Link>
        ))}

        {/* User */}
        <div className="mt-4 p-3 bg-white/5 rounded-lg">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-aegis-primary rounded-full flex items-center justify-center text-sm font-bold">
              AD
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">Admin User</p>
              <p className="text-xs text-gray-400 truncate">admin@aegis.health</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
