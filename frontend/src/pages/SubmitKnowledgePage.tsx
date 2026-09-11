import { useState } from 'react'
import { fetchApi } from '@/shared/api/client'
import { useRole } from '@/shared/lib/roles'
import { RuleResultChecklist, type RuleResult } from '@/shared/ui/RuleResultChecklist'
import { StatusBadge, type StatusValue } from '@/shared/ui/StatusBadge'
import { Loader2, BookOpen } from 'lucide-react'
import { PageShell } from './ConsolePage'

export function SubmitKnowledgePage() {
  const { role } = useRole()
  const [content, setContent] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const [result, setResult] = useState<{
    submission_id: string
    status: string
    rule_results: RuleResult[]
  } | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setError(null)
    setResult(null)

    if (content.trim().length < 20 || content.trim().length > 4000) {
      setError('Content must be between 20 and 4000 characters.')
      setIsSubmitting(false)
      return
    }

    try {
      const response = await fetchApi<any>('/api/v1/knowledge/submissions', {
        method: 'POST',
        body: JSON.stringify({
          submitted_by: `${role}-frontend-user`,
          submitter_role: role,
          raw_content: content.trim(),
        }),
      })

      setResult(response)
      setContent('')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <PageShell
      icon={BookOpen}
      title="Submit Knowledge"
      label="KNOWLEDGE BASE CURATION WORKFLOW"
    >
      <div className="p-6 max-w-3xl mx-auto space-y-6">
        <div className="space-y-1">
          <p className="text-sm text-text-secondary">Propose new information for the knowledge base. Content is instantly evaluated.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="label-caps block">Raw Content</label>
            <textarea
              className="w-full h-40 bg-base-800 border border-border rounded-sm p-3 text-sm text-text-primary focus:border-amber focus:ring-1 focus:ring-amber outline-none resize-y font-sans"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Enter facts, rules, or instructions here (min 20 characters)..."
              disabled={isSubmitting}
            />
          </div>

          {error && (
            <div className="p-3 rounded-sm bg-rose/10 border border-rose/30 text-rose text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={isSubmitting || !content.trim()}
            className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-amber hover:bg-amber-light text-base-900 rounded-sm text-sm font-bold tracking-tight disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
            Submit for Review
          </button>
        </form>

        {result && (
          <div className="mt-8 space-y-4 p-5 bg-base-800 border border-border rounded-sm shadow-sm">
            <div className="flex items-center justify-between border-b border-border-subtle pb-3">
              <h2 className="text-sm font-bold text-text-primary uppercase tracking-wider">Submission Result</h2>
              <StatusBadge status={result.status as StatusValue} />
            </div>
            
            <div className="space-y-2">
              <div className="text-xs text-text-muted mono uppercase">Rule Evaluation Breakdown</div>
              <RuleResultChecklist results={result.rule_results} />
            </div>
          </div>
        )}
      </div>
    </PageShell>
  )
}
