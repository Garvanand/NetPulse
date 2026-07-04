import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Map, Share2, AlertTriangle, Activity } from 'lucide-react'

export function Navigation() {
  const pathname = usePathname()

  const links = [
    { href: '/dashboard', label: 'Overview', icon: Activity },
    { href: '/map', label: 'Live Map', icon: Map },
    { href: '/topology', label: 'Topology', icon: Share2 },
    { href: '/incidents', label: 'Incidents', icon: AlertTriangle },
  ]

  return (
    <nav className="h-16 border-b border-zinc-800 bg-zinc-950 flex items-center px-6 justify-between">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center">
          <Activity className="w-5 h-5 text-white" />
        </div>
        <span className="text-xl font-bold text-white tracking-tight">NetPulse</span>
      </div>
      
      <div className="flex gap-1">
        {links.map((link) => {
          const Icon = link.icon
          const isActive = pathname?.startsWith(link.href)
          
          return (
            <Link 
              key={link.href}
              href={link.href}
              className={`px-4 py-2 rounded-md flex items-center gap-2 text-sm transition-colors ${
                isActive 
                  ? 'bg-zinc-800 text-white font-medium' 
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900'
              }`}
            >
              <Icon className="w-4 h-4" />
              {link.label}
            </Link>
          )
        })}
      </div>
      
      <div className="flex items-center gap-4">
        <div className="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700"></div>
      </div>
    </nav>
  )
}
