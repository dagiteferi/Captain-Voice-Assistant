import { useState, useEffect } from 'react'
import { fetchApi } from '@/shared/api/client'
import { useRole } from '@/shared/lib/roles'
import { StatusBadge, type StatusValue } from '@/shared/ui/StatusBadge'
import { RuleResultChecklist, type RuleResult } from '@/shared/ui/RuleResultChecklist'
import { Loader2, AlertCircle, ChevronDown, ChevronRight, CheckCircle, XCircle, ClipboardCheck } from 'lucide-react'
import { PageShell } from './ConsolePage'

interface SubmissionList {
  id: string
  submitted_by: string
  submitter_role: string
  raw_content: string
  status: string
  created_at: string
}

interface SubmissionDetail extends SubmissionList {
  rule_results: RuleResult[]
  reviewed_by: string | null
}

export function ReviewQueuePage() {
  const { role } = useRole()
  const [submissions, setSubmissions] = useState<SubmissionList[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [details, setDetails] = useState<Record<string, SubmissionDetail>>({})
  const [loadingDetails, setLoadingDetails] = useState<Record<string, boolean>>({})

  useEffect(() => {
    if (role !== 'captain') {
      setIsLoading(false)
      return
    }

    const loadQueue = async () => {
      setIsLoading(true)
      try {
        const data = await fetchApi<{ submissions: SubmissionList[] }>('/api/v1/knowledge/submissions?status=pending', { role })
        setSubmissions(data.submissions || [])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load queue')
      } finally {
        setIsLoading(false)
      }
    }
    
    loadQueue()
  }, [role])

  const toggleExpand = async (id: string) => {
    if (expandedId === id) {
      setExpandedId(null)
      return
    }
    
    setExpandedId(id)
    
    if (!details[id]) {
      setLoadingDetails(prev => ({ ...prev, [id]: true }))
      try {
        const data = await fetchApi<SubmissionDetail>(`/api/v1/knowledge/submissions/${id}`, { role })
        setDetails(prev => ({ ...prev, [id]: data }))
      } catch (err) {
        console.error(err)
      } finally {
        setLoadingDetails(prev => ({ ...prev, [id]: false }))
      }
    }
  }

  const handleAction = async (id: string, action: 'approve' | 'reject') => {
    try {
      await fetchApi(`/api/v1/knowledge/submissions/${id}/${action}`, {
        method: 'POST',
        role,
        body: JSON.stringify({ reviewed_by: 'captain-frontend' })
      })
      
      setSubmissions(prev => prev.filter(s => s.id !== id))
      if (expandedId === id) setExpandedId(null)
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Action failed')
    }
  }

  if (role !== 'captain') {
    return (
      <PageShell
        icon={ClipboardCheck}
        title="Review Queue"
        label="CAPTAIN KNOWLEDGE CURATION"
      >
        <div className="p-6 flex items-center justify-center h-full">
          <div className="text-center space-y-3">
            <AlertCircle className="h-10 w-10 text-rose mx-auto" />
            <h2 className="text-lg font-medium text-text-primary">Access Denied</h2>
            <p className="text-sm text-text-secondary">Only Captains can access the review queue.</p>
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
    >
      <div className="p-6 max-w-4xl mx-auto space-y-6">
        <div className="space-y-1">
          <p className="text-sm text-text-secondary">Review pending knowledge submissions from the crew and guests.</p>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="h-6 w-6 animate-spin text-amber" />
          </div>
        ) : error ? (
          <div className="p-4 rounded-sm bg-rose/10 border border-rose/30 text-rose text-sm">
            {error}
          </div>
        ) : submissions.length === 0 ? (
          <div className="p-12 text-center border border-dashed border-border-subtle rounded-sm bg-base-800/50">
            <p className="text-text-muted text-sm">No pending submissions in the queue.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {submissions.map(sub => (
              <div key={sub.id} className="border border-border bg-base-800 rounded-sm overflow-hidden">
                <div 
                  className="p-4 flex items-center justify-between cursor-pointer hover:bg-base-700 transition-colors"
                  onClick={() => toggleExpand(sub.id)}
                >
                  <div className="flex items-center gap-4">
                    {expandedId === sub.id ? <ChevronDown className="h-4 w-4 text-text-muted" /> : <ChevronRight className="h-4 w-4 text-text-muted" />}
                    <div className="space-y-1">
                      <div className="text-sm font-medium text-text-primary line-clamp-1">{sub.raw_content}</div>
                      <div className="flex items-center gap-3 text-xs text-text-muted mono">
                        <span>By: {sub.submitted_by} ({sub.submitter_role})</span>
                        <span>•</span>
                        <span>{new Date(sub.created_at).toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                  <StatusBadge status={sub.status as StatusValue} />
                </div>

                {expandedId === sub.id && (
                  <div className="p-4 border-t border-border-subtle bg-base-900/50 space-y-6">
                    <div>
                      <h3 className="label-caps mb-2">Raw Content</h3>
                      <div className="p-3 bg-base-800 border border-border rounded-sm text-sm text-text-primary whitespace-pre-wrap font-sans">
                        {sub.raw_content}
                      </div>
                    </div>

                    {loadingDetails[sub.id] ? (
                      <div className="flex items-center gap-2 text-text-muted text-sm">
                        <Loader2 className="h-4 w-4 animate-spin" /> Loading rules...
                      </div>
                    ) : details[sub.id] ? (
                      <div>
                        <h3 className="label-caps mb-2">Rule Evaluation</h3>
                        <RuleResultChecklist results={details[sub.id].rule_results} />
                      </div>
                    ) : null}

                    <div className="flex items-center justify-end gap-3 pt-2">
                      <button
                        onClick={() => handleAction(sub.id, 'reject')}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-rose/30 text-rose hover:bg-rose/10 rounded-sm text-sm font-medium transition-colors"
                      >
                        <XCircle className="h-4 w-4" /> Reject
                      </button>
                      <button
                        onClick={() => handleAction(sub.id, 'approve')}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald hover:bg-emerald/90 text-base-900 rounded-sm text-sm font-bold transition-colors"
                      >
                        <CheckCircle className="h-4 w-4" /> Approve
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </PageShell>
  )
}
