import { CheckCircle2, XCircle } from 'lucide-react'
import { cn } from '@/shared/lib/cn'

export interface RuleResult {
  rule: string
  outcome: 'pass' | 'fail' | 'error' | string
  similarity?: number | null
  detail?: string | null
}

interface RuleResultChecklistProps {
  results?: RuleResult[] | null
  className?: string
}

export function RuleResultChecklist({ results, className }: RuleResultChecklistProps) {
  if (!results || results.length === 0) {
    return (
      <div className={cn('text-sm text-text-muted italic', className)}>
        No rule results available.
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      {results.map((res, i) => {
        const isPass = res.outcome === 'pass'
        const Icon = isPass ? CheckCircle2 : XCircle
        const colorClass = isPass ? 'text-emerald' : 'text-rose'
        const bgClass = isPass ? 'bg-emerald/10' : 'bg-rose/10'
        const borderClass = isPass ? 'border-emerald/20' : 'border-rose/20'

        return (
          <div
            key={i}
            className={cn(
              'flex items-center gap-3 p-2 rounded-sm border text-sm',
              bgClass,
              borderClass
            )}
          >
            <Icon className={cn('h-4 w-4 flex-shrink-0', colorClass)} />
            <div className="flex-1 flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <span className="font-medium text-text-primary">{res.rule}</span>
              <div className="flex items-center gap-3 text-xs">
                {res.similarity !== undefined && res.similarity !== null && (
                  <span className="text-text-secondary mono bg-base-800 px-1.5 py-0.5 rounded border border-border">
                    sim: {res.similarity.toFixed(3)}
                  </span>
                )}
                <span className={cn('mono uppercase tracking-wider', colorClass)}>
                  {res.outcome}
                </span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
