import { useState, useEffect } from 'react'
import {
  ClipboardCheck,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronRight,
  Shield,
  Filter,
  RefreshCw,
  UserCheck,
} from 'lucide-react'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { PageShell } from './ConsolePage'
import { useRole } from '@/shared/lib/roles'
import {
  getSubmissions,
  approveSubmission,
  rejectSubmission,
} from '@/entities/knowledge/api/knowledgeApi'
import type { SubmissionItem } from '@/entities/knowledge/model/types'

export function ReviewQueuePage() {
  const { role } = useRole()
  const [filter, setFilter] = useState<'pending' | 'approved' | 'rejected' | 'all'>('pending')
  const [submissions, setSubmissions] = useState<SubmissionItem[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedItems, setExpandedItems] = useState<Record<string, boolean>>({})
  const [rejectingId, setRejectingId] = useState<string | null>(null)
  const [rejectReason, setRejectReason] = useState('')

  const loadSubmissions = async () => {
    if (role !== 'captain') return
    setLoading(true)
    try {
      const data = await getSubmissions(filter, role)
      setSubmissions(data.submissions)
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to fetch review queue')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSubmissions()
  }, [filter, role])

  const toggleExpand = (id: string) => {
    setExpandedItems((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const handleApprove = async (id: string) => {
    try {
      await approveSubmission(id, 'captain-main', role)
      loadSubmissions()
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Approve failed')
    }
  }

  const handleRejectSubmit = async (id: string) => {
    try {
      await rejectSubmission(id, 'captain-main', rejectReason, role)
      setRejectingId(null)
      setRejectReason('')
      loadSubmissions()
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Reject failed')
    }
  }

  if (role !== 'captain') {
    return (
      <PageShell
        icon={ClipboardCheck}
        title="Review Queue"
        label="CAPTAIN KNOWLEDGE CURATION"
        badge={<StatusBadge status="failed" size="sm" />}
      >
        <div className="panel p-8 text-center space-y-4">
          <Shield className="h-8 w-8 text-amber mx-auto" />
          <div className="space-y-1">
            <h2 className="text-base font-semibold text-text-primary">
              Captain Role Required
            </h2>
            <p className="text-text-secondary text-sm max-w-md mx-auto">
              The Knowledge Base Review Queue is restricted to system Captains. Switch your role using the header selector to review pending submissions.
            </p>
          </div>
        </div>
      </PageShell>
    )
  }

  return (
    <PageShell
      icon={ClipboardCheck}
      title="Review Queue"
      label="CAPTAIN KNOWLEDGE CURATION"
      badge={
        <span className="mono text-xs px-2 py-0.5 rounded bg-amber/10 border border-amber/30 text-amber font-semibold">
          CAPTAIN ACCESS
        </span>
      }
    >
      <div className="space-y-4 animate-fade-in">
        {/* Controls Bar */}
        <div className="panel p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-base-800">
          <div className="flex items-center gap-1">
            <Filter className="h-3.5 w-3.5 text-text-muted mr-1 ml-1" />
            {(['pending', 'approved', 'rejected', 'all'] as const).map((st) => (
              <button
                key={st}
                onClick={() => setFilter(st)}
                className={`px-3 py-1 rounded text-xs capitalize transition-colors ${
                  filter === st
                    ? 'bg-amber/20 border border-amber/40 text-amber font-medium'
                    : 'text-text-secondary hover:text-text-primary hover:bg-base-700'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

          <button
            onClick={loadSubmissions}
            disabled={loading}
            className="btn-secondary text-xs"
            title="Refresh List"
          >
            <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
            Refresh Queue
          </button>
        </div>

        {/* Submissions List */}
        <div className="space-y-3">
          {submissions.length === 0 ? (
            <div className="panel p-8 text-center text-text-muted text-sm">
              No submissions found for status filter <strong className="text-amber">"{filter}"</strong>.
            </div>
          ) : (
            submissions.map((item) => {
              const isExpanded = !!expandedItems[item.id]
              const isPending = item.status === 'pending'

              return (
                <div key={item.id} className="panel p-4 space-y-3 bg-base-800/90 border border-border">
                  {/* Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2 border-b border-border-subtle">
                    <div className="flex items-center gap-2">
                      <span className="mono text-xs font-semibold text-amber">{item.id}</span>
                      <span className="mono text-[10px] px-1.5 py-0.5 rounded bg-base-700 text-text-secondary border border-border">
                        Role: {item.submitter_role}
                      </span>
                      <StatusBadge status={item.status} size="sm" />
                    </div>

                    <div className="flex items-center gap-2 text-text-muted text-[11px] mono">
                      <UserCheck className="h-3 w-3 text-text-muted" />
                      <span>{item.submitted_by}</span>
                      <span>•</span>
                      <span>{new Date(item.created_at).toLocaleTimeString()}</span>
                    </div>
                  </div>

                  {/* Raw Content Quote Box */}
                  <div className="p-3 rounded bg-base-900 border border-border text-xs text-text-primary leading-relaxed font-sans">
                    "{item.raw_content}"
                  </div>

                  {/* Rule Results Toggle */}
                  {item.rule_results && item.rule_results.length > 0 && (
                    <div className="space-y-2">
                      <button
                        onClick={() => toggleExpand(item.id)}
                        className="flex items-center gap-1.5 text-xs text-amber font-mono hover:underline"
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-3.5 w-3.5" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5" />
                        )}
                        Rule Engine Evaluation ({item.rule_results.length} checks)
                      </button>

                      {isExpanded && (
                        <div className="grid gap-2 sm:grid-cols-2 pt-1 animate-fade-in">
                          {item.rule_results.map((r, i) => (
                            <div
                              key={i}
                              className="p-2 rounded bg-base-900/80 border border-border text-[11px] flex items-center gap-2"
                            >
                              {r.outcome === 'pass' ? (
                                <CheckCircle2 className="h-3.5 w-3.5 text-emerald flex-shrink-0" />
                              ) : (
                                <XCircle className="h-3.5 w-3.5 text-rose flex-shrink-0" />
                              )}
                              <div className="space-y-0.5 min-w-0">
                                <span className="mono font-semibold text-text-primary">{r.rule}</span>
                                {r.details && (
                                  <p className="text-text-secondary truncate text-[10px]">
                                    {r.details}
                                  </p>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Actions for Pending Submissions */}
                  {isPending && (
                    <div className="pt-2 border-t border-border-subtle flex items-center justify-end gap-2">
                      {rejectingId === item.id ? (
                        <div className="flex items-center gap-2 w-full max-w-md">
                          <input
                            type="text"
                            value={rejectReason}
                            onChange={(e) => setRejectReason(e.target.value)}
                            placeholder="Reason for rejection..."
                            className="input-field text-xs flex-1"
                          />
                          <button
                            onClick={() => handleRejectSubmit(item.id)}
                            className="btn-primary bg-rose hover:bg-rose/80 text-white text-xs py-1"
                          >
                            Confirm Reject
                          </button>
                          <button
                            onClick={() => setRejectingId(null)}
                            className="btn-secondary text-xs py-1"
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <>
                          <button
                            onClick={() => setRejectingId(item.id)}
                            className="btn-secondary text-xs border-rose/30 text-rose hover:bg-rose/10"
                          >
                            <XCircle className="h-3.5 w-3.5" />
                            Reject Proposal
                          </button>
                          <button
                            onClick={() => handleApprove(item.id)}
                            className="btn-primary text-xs"
                          >
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Approve & Index
                          </button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              )
            })
          )}
        </div>
      </div>
    </PageShell>
  )
}
