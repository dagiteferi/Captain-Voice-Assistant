import { Anchor, Users, UserX } from 'lucide-react'
import { type UserRole, ROLE_META, useRole } from '@/shared/lib/roles'
import { cn } from '@/shared/lib/cn'

const ROLE_ICONS: Record<UserRole, React.ComponentType<{ className?: string }>> = {
  captain: Anchor,
  crew: Users,
  guest: UserX,
}

interface RoleBadgeProps {
  role: UserRole
  className?: string
  compact?: boolean
}

export function RoleBadge({ role, className, compact = false }: RoleBadgeProps) {
  const meta = ROLE_META[role]
  const Icon = ROLE_ICONS[role]

  const colorMap: Record<UserRole, string> = {
    captain: 'text-amber border-amber/40 bg-amber/8',
    crew: 'text-sky border-sky/40 bg-sky/8',
    guest: 'text-slate border-slate/40 bg-slate/8',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-[2px] border px-2 py-0.5',
        colorMap[role],
        className,
      )}
    >
      <Icon className="h-3 w-3 flex-shrink-0" />
      {!compact && (
        <span className="mono text-[11px] font-medium uppercase tracking-wider">
          {meta.label}
        </span>
      )}
    </span>
  )
}

/** Role switcher control — for use in the header */
export function RoleSwitcher() {
  const { role, setRole } = useRole()
  const roles: UserRole[] = ['captain', 'crew', 'guest']

  return (
    <div className="flex items-center gap-1 rounded-sm bg-base-700 border border-border p-0.5">
      {roles.map((r) => {
        const Icon = ROLE_ICONS[r]
        const isActive = role === r
        const activeColors: Record<UserRole, string> = {
          captain: 'bg-amber/15 text-amber border-amber/30',
          crew: 'bg-sky/15 text-sky border-sky/30',
          guest: 'bg-slate/15 text-slate border-slate/30',
        }

        return (
          <button
            key={r}
            onClick={() => setRole(r)}
            title={ROLE_META[r].description}
            className={cn(
              'flex items-center gap-1.5 px-2.5 py-1 rounded-[2px] border transition-all duration-150',
              'text-xs font-medium',
              isActive
                ? activeColors[r]
                : 'border-transparent text-text-secondary hover:text-text-primary hover:bg-base-600',
            )}
          >
            <Icon className="h-3 w-3" />
            <span className="hidden sm:inline mono tracking-wider uppercase" style={{ fontSize: 10 }}>
              {r}
            </span>
          </button>
        )
      })}
    </div>
  )
}
