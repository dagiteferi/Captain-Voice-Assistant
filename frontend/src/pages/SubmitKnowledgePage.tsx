import { useState } from 'react'
import { BookOpen, CheckCircle2, XCircle, FilePlus, Send, Database, Sparkles } from 'lucide-react'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { PageShell } from './ConsolePage'
import { useRole } from '@/shared/lib/roles'
import { submitKnowledge, bulkIngestDocuments } from '@/entities/knowledge/api/knowledgeApi'
import type { RuleResult } from '@/entities/knowledge/model/types'

export function SubmitKnowledgePage() {
  const { role } = useRole()
  const [submitterId, setSubmitterId] = useState(`${role}-user-1`)
  const [rawContent, setRawContent] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [lastSubmissionResult, setLastSubmissionResult] = useState<{
    id: string
    status: 'pending' | 'approved' | 'rejected' | 'indexed'
    rule_results: RuleResult[]
  } | null>(null)

  // Bulk Ingestion state (Captain only)
  const [bulkTitle, setBulkTitle] = useState('')
  const [bulkContent, setBulkContent] = useState('')
  const [bulkIngestResult, setBulkIngestResult] = useState<string | null>(null)

  const charCount = rawContent.trim().length
  const isValidLength = charCount >= 20 && charCount <= 4000

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isValidLength || isSubmitting) return

    setIsSubmitting(true)
    try {
      const res = await submitKnowledge(
        {
          submitted_by: submitterId || `${role}-user-1`,
          submitter_role: role,
          raw_content: rawContent.trim(),
        },
        role,
      )

      setLastSubmissionResult({
        id: res.submission_id,
        status: res.status,
        rule_results: res.rule_results,
      })
      setRawContent('')
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Knowledge submission failed')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleBulkSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!bulkTitle.trim() || !bulkContent.trim()) return

    try {
      const res = await bulkIngestDocuments([{ title: bulkTitle.trim(), content: bulkContent.trim() }], role)
      setBulkIngestResult(`Successfully ingested ${res.ingested_count} document directly into Knowledge Base. (IDs: ${res.document_ids.join(', ')})`)
      setBulkTitle('')
      setBulkContent('')
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Bulk ingestion failed')
    }
  }

  return (
    <PageShell
      icon={BookOpen}
      title="Submit Knowledge"
      label="KNOWLEDGE BASE CURATION WORKFLOW"
      badge={
        <span className="mono text-xs px-2 py-0.5 rounded bg-amber/10 border border-amber/30 text-amber">
          ROLE: {role.toUpperCase()}
        </span>
      }
    >
      <div className="space-y-6 animate-fade-in">
        {/* Knowledge Proposal Form Panel */}
        <div className="panel p-5 space-y-4 border-l-2 border-l-amber">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-amber" />
              <h2 className="text-sm font-semibold text-text-primary">Propose Knowledge Addition</h2>
            </div>
            <span className="mono text-[11px] text-text-muted">Runs Rule Engine on Submit</span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid sm:grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="label-caps">Submitter ID / Name</label>
                <input
                  type="text"
                  value={submitterId}
                  onChange={(e) => setSubmitterId(e.target.value)}
                  placeholder="e.g. officer-sarah"
                  className="input-field w-full text-xs"
                />
              </div>

              <div className="space-y-1">
                <label className="label-caps">Submitter Role</label>
                <input
                  type="text"
                  value={role.toUpperCase()}
                  disabled
                  className="input-field w-full text-xs uppercase bg-base-800 font-mono text-amber"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="label-caps">Raw Knowledge Content (20–4000 chars)</label>
                <span
                  className={`mono text-[11px] ${
                    isValidLength ? 'text-text-secondary' : 'text-rose font-semibold'
                  }`}
                >
                  {charCount} / 4000 chars
                </span>
              </div>
              <textarea
                value={rawContent}
                onChange={(e) => setRawContent(e.target.value)}
                placeholder="Enter maritime operational procedures, port contacts, or vessel rules..."
                className="input-field w-full h-32 resize-none text-xs focus:border-amber transition-all"
              />
            </div>

            {/* Quick preset buttons */}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <span className="mono text-[10px] text-text-muted">Insert Preset:</span>
              <button
                type="button"
                onClick={() =>
                  setRawContent(
                    'Port Authority contact for Djibouti anchorage control: VHF Channel 12. Main Office Phone: +253 21 350000. Operational 24/7.',
                  )
                }
                className="btn-secondary text-[11px] py-0.5 px-2"
              >
                Port Contact
              </button>
              <button
                type="button"
                onClick={() =>
                  setRawContent(
                    'Vessel Alpha auxiliary generator start procedure: Check coolant level, verify battery voltage > 24V, turn ignition switch to position B for 3 seconds.',
                  )
                }
                className="btn-secondary text-[11px] py-0.5 px-2"
              >
                Engine SOP
              </button>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={!isValidLength || isSubmitting}
                className="btn-primary"
              >
                <Send className="h-3.5 w-3.5" />
                Submit Knowledge Proposal
              </button>
            </div>
          </form>
        </div>

        {/* Rule Evaluation Breakdown Card */}
        {lastSubmissionResult && (
          <div className="panel p-5 space-y-4 bg-base-800/90 border border-amber/40 animate-fade-in">
            <div className="flex items-center justify-between pb-3 border-b border-border">
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-text-primary">
                  Rule Engine Results for {lastSubmissionResult.id}
                </h3>
                <StatusBadge status={lastSubmissionResult.status} />
              </div>
              <span className="mono text-[11px] text-text-muted">Rule Evaluation Complete</span>
            </div>

            <div className="grid gap-2 sm:grid-cols-2">
              {lastSubmissionResult.rule_results.map((rule, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded bg-base-900 border border-border flex items-start gap-2.5"
                >
                  {rule.outcome === 'pass' ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald flex-shrink-0 mt-0.5" />
                  ) : (
                    <XCircle className="h-4 w-4 text-rose flex-shrink-0 mt-0.5" />
                  )}
                  <div className="space-y-0.5">
                    <p className="mono text-xs font-semibold text-text-primary">{rule.rule}</p>
                    <p className="text-[11px] text-text-secondary">
                      {rule.details || `Outcome: ${rule.outcome}`}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <div className="p-3 rounded bg-base-700/50 border border-border text-xs text-text-secondary">
              {lastSubmissionResult.status === 'approved' && (
                <p className="text-emerald font-medium">
                  ✓ Approved & Indexed directly into Knowledge Vector Store (Captain Auto-Approve).
                </p>
              )}
              {lastSubmissionResult.status === 'pending' && (
                <p className="text-amber font-medium">
                  ⏳ Pending Captain Review — Sent to Captain Review Queue.
                </p>
              )}
              {lastSubmissionResult.status === 'rejected' && (
                <p className="text-rose font-medium">
                  ✕ Rejected by Rule Engine rules (hard rule check failed).
                </p>
              )}
            </div>
          </div>
        )}

        {/* Captain Only: Bulk Ingestion Section */}
        {role === 'captain' && (
          <div className="panel p-5 space-y-4 border-l-2 border-l-sky bg-sky/5">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4 text-sky" />
              <h2 className="text-sm font-semibold text-text-primary">
                Bulk Document Seeding (Captain Only)
              </h2>
            </div>
            <p className="text-xs text-text-secondary">
              Directly ingest verified documents into the vector store, bypassing the review queue.
            </p>

            <form onSubmit={handleBulkSubmit} className="space-y-3">
              <div className="space-y-1">
                <label className="label-caps">Document Title</label>
                <input
                  type="text"
                  value={bulkTitle}
                  onChange={(e) => setBulkTitle(e.target.value)}
                  placeholder="e.g. SOLAS Safety Convention Chapter III"
                  className="input-field w-full text-xs"
                />
              </div>

              <div className="space-y-1">
                <label className="label-caps">Full Document Content</label>
                <textarea
                  value={bulkContent}
                  onChange={(e) => setBulkContent(e.target.value)}
                  placeholder="Paste complete document text for embedding..."
                  className="input-field w-full h-24 text-xs resize-none"
                />
              </div>

              <button
                type="submit"
                disabled={!bulkTitle.trim() || !bulkContent.trim()}
                className="btn-primary bg-sky hover:bg-sky-light text-base-900 font-semibold"
              >
                <FilePlus className="h-3.5 w-3.5" />
                Ingest Seed Document
              </button>
            </form>

            {bulkIngestResult && (
              <div className="p-3 rounded bg-emerald/10 border border-emerald/30 text-emerald text-xs font-mono">
                {bulkIngestResult}
              </div>
            )}
          </div>
        )}
      </div>
    </PageShell>
  )
}
