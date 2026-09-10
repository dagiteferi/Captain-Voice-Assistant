import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Loader2,
  Database,
} from 'lucide-react'
import { cn } from '@/shared/lib/cn'

export type StatusValue =
  | 'pending'
  | 'grounded'
  | 'ungrounded'
  | 'failed'
  | 'approved'
  | 'rejected'
  | 'indexed'
  | 'in_flight'

interface StatusConfig {
  label: string
  icon: React.ComponentType<{ className?: string }>
  dotClass: string
  textClass: string
  bgClass: string
  borderClass: string
  spin?: boolean
}

const STATUS_CONFIG: Record<StatusValue, StatusConfig> = {
  grounded: {
    label: 'Grounded',
    icon: CheckCircle2,
    dotClass: 'bg-amber',
    textClass: 'text-amber',
    bgClass: 'bg-amber/10',
    borderClass: 'border-amber/30',
  },
  approved: {
    label: 'Approved',
    icon: CheckCircle2,
    dotClass: 'bg-emerald',
    textClass: 'text-emerald',
    bgClass: 'bg-emerald/10',
    borderClass: 'border-emerald/30',
  },
  indexed: {
    label: 'Indexed',
    icon: Database,
    dotClass: 'bg-emerald',
    textClass: 'text-emerald',
    bgClass: 'bg-emerald/10',
    borderClass: 'border-emerald/30',
  },
  pending: {
    label: 'Pending',
    icon: Clock,
    dotClass: 'bg-slate',
    textClass: 'text-slate',
    bgClass: 'bg-slate/10',
    borderClass: 'border-slate/30',
  },
  in_flight: {
    label: 'Running',
    icon: Loader2,
    dotClass: 'bg-sky',
    textClass: 'text-sky',
    bgClass: 'bg-sky/10',
    borderClass: 'border-sky/30',
    spin: true,
  },
  ungrounded: {
    label: 'Ungrounded',
    icon: AlertTriangle,
    dotClass: 'bg-rose',
    textClass: 'text-rose',
    bgClass: 'bg-rose/10',
    borderClass: 'border-rose/30',
  },
  rejected: {
    label: 'Rejected',
    icon: XCircle,
    dotClass: 'bg-rose',
    textClass: 'text-rose',
    bgClass: 'bg-rose/10',
    borderClass: 'border-rose/30',
  },
  failed: {
    label: 'Failed',
    icon: XCircle,
    dotClass: 'bg-rose',
    textClass: 'text-rose',
    bgClass: 'bg-rose/10',
    borderClass: 'border-rose/30',
  },
}

interface StatusBadgeProps {
  status: StatusValue
  size?: 'sm' | 'md'
  showLabel?: boolean
  className?: string
}

export function StatusBadge({
  status,
  size = 'md',
  showLabel = true,
  className,
}: StatusBadgeProps) {
  const cfg = STATUS_CONFIG[status]
  const Icon = cfg.icon

  if (size === 'sm') {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1 rounded-[2px] border px-1.5 py-0.5',
          cfg.bgClass,
          cfg.borderClass,
          className,
        )}
        title={cfg.label}
      >
        <Icon
          className={cn('h-3 w-3 flex-shrink-0', cfg.textClass, cfg.spin && 'animate-spin')}
        />
        {showLabel && (
          <span className={cn('mono text-[11px] font-medium', cfg.textClass)}>
            {cfg.label}
          </span>
        )}
      </span>
    )
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-sm border px-2 py-1',
        cfg.bgClass,
        cfg.borderClass,
        className,
      )}
    >
      <Icon
        className={cn('h-3.5 w-3.5 flex-shrink-0', cfg.textClass, cfg.spin && 'animate-spin')}
      />
      {showLabel && (
        <span className={cn('text-xs font-medium', cfg.textClass)}>{cfg.label}</span>
      )}
    </span>
  )
}

/** Dot-only variant for compact contexts */
export function StatusDot({ status, className }: { status: StatusValue; className?: string }) {
  const cfg = STATUS_CONFIG[status]
  return (
    <span
      className={cn('status-dot flex-shrink-0', cfg.dotClass, className)}
      title={cfg.label}
    />
  )
}

export { STATUS_CONFIG }
