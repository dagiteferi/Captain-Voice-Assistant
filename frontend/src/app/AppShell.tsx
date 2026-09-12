import { NavLink } from 'react-router-dom'
import {
  Terminal,
  GitBranch,
  BookOpen,
  ClipboardCheck,
  Radio,
  Circle,
  Database,
} from 'lucide-react'
import { RoleSwitcher, RoleBadge } from '@/shared/ui/RoleBadge'
import { useRole } from '@/shared/lib/roles'
import { cn } from '@/shared/lib/cn'

interface NavItem {
  to: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  requiresCaptain?: boolean
  tooltip?: string
}

const NAV_ITEMS: NavItem[] = [
  { to: '/console', label: 'Console', icon: Terminal },
  { to: '/trace', label: 'Trace', icon: GitBranch },
  { to: '/submit-knowledge', label: 'Submit Knowledge', icon: BookOpen },
  { to: '/manage-knowledge', label: 'Manage Knowledge', icon: Database },
  {
    to: '/review-queue',
    label: 'Review Queue',
    icon: ClipboardCheck,
    requiresCaptain: true,
    tooltip: 'Captain access only',
  },
]


export function AppShell({ children }: { children: React.ReactNode }) {
  const { role } = useRole()

  return (
    <div className="flex flex-col min-h-screen bg-base-900">
      <TopBar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar role={role} />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  )
}

function TopBar() {
  const { role } = useRole()

  return (
    <header className="flex items-center justify-between h-12 px-4 border-b border-border bg-base-800 flex-shrink-0 z-10">
      {/* Wordmark */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Radio className="h-4 w-4 text-amber" />
          <span className="font-semibold text-text-primary tracking-tight" style={{ fontSize: 13 }}>
            CAPTAIN
          </span>
          <span
            className="mono text-text-muted"
            style={{ fontSize: 10, letterSpacing: '0.1em' }}
          >
            VOICE INTELLIGENCE CONSOLE
          </span>
        </div>
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-3">
        {/* System health indicator */}
        <div className="hidden md:flex items-center gap-1.5 text-emerald">
          <Circle className="h-2 w-2 fill-current" />
          <span className="mono text-[11px] text-text-secondary">SYS ONLINE</span>
        </div>

        <div className="w-px h-4 bg-border" />

        <RoleSwitcher />

        <div className="hidden md:block">
          <RoleBadge role={role} compact />
        </div>
      </div>
    </header>
  )
}

function Sidebar({ role }: { role: ReturnType<typeof useRole>['role'] }) {
  return (
    <nav className="w-48 flex-shrink-0 border-r border-border bg-base-800 flex flex-col py-3 px-2">
      <div className="space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const isLocked = item.requiresCaptain && role !== 'captain'

          if (isLocked) {
            return (
              <div
                key={item.to}
                className="flex items-center gap-2 px-3 py-2 rounded-sm text-text-muted cursor-not-allowed opacity-50"
                title={item.tooltip}
              >
                <Icon className="h-3.5 w-3.5" />
                <span className="text-sm font-medium">{item.label}</span>
              </div>
            )
          }

          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-2 px-3 py-2 rounded-sm text-sm font-medium transition-all duration-150',
                  isActive
                    ? 'text-text-primary bg-base-700 shadow-[inset_2px_0_0_#f59e0b]'
                    : 'text-text-secondary hover:text-text-primary hover:bg-base-700',
                )
              }
            >
              <Icon className="h-3.5 w-3.5 flex-shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          )
        })}
      </div>

      {/* Bottom: role info */}
      <div className="mt-auto pt-4 border-t border-border-subtle px-2">
        <div className="space-y-1">
          <p className="label-caps">Active Role</p>
          <RoleBadge role={role} />
        </div>
      </div>
    </nav>
  )
}
