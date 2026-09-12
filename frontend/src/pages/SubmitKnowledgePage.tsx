import { useState } from 'react'
import { fetchApi } from '@/shared/api/client'
import { useRole } from '@/shared/lib/roles'
import { RuleResultChecklist, type RuleResult } from '@/shared/ui/RuleResultChecklist'
import { StatusBadge, type StatusValue } from '@/shared/ui/StatusBadge'
import { Loader2, BookOpen, FileText, Upload, Link, ListOrdered, Plus, Trash2 } from 'lucide-react'
import { PageShell } from './ConsolePage'

type SubmissionMode = 'text' | 'file' | 'url' | 'procedure'

export function SubmitKnowledgePage() {
  const { role } = useRole()
  const [mode, setMode] = useState<SubmissionMode>('text')
  
  // State for Mode 1: Text
  const [content, setContent] = useState('')
  
  // State for Mode 2: File Upload
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  
  // State for Mode 3: URL
  const [url, setUrl] = useState('')
  
  // State for Mode 4: Structured Procedure Form
  const [sopTitle, setSopTitle] = useState('')
  const [sopCategory, setSopCategory] = useState('Engine Operation')
  const [sopSeverity, setSopSeverity] = useState('Priority')
  const [sopSteps, setSopSteps] = useState<string[]>([''])
  const [sopNotes, setSopNotes] = useState('')

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  
  const [result, setResult] = useState<{
    submission_id: string
    status: string
    rule_results: RuleResult[]
  } | null>(null)

  const handleAddStep = () => {
    setSopSteps([...sopSteps, ''])
  }

  const handleRemoveStep = (index: number) => {
    setSopSteps(sopSteps.filter((_, i) => i !== index))
  }

  const handleStepChange = (index: number, value: string) => {
    const updated = [...sopSteps]
    updated[index] = value
    setSopSteps(updated)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)
    setError(null)
    setResult(null)

    try {
      let response: any

      if (mode === 'text') {
        if (content.trim().length < 20 || content.trim().length > 4000) {
          setError('Content must be between 20 and 4000 characters.')
          setIsSubmitting(false)
          return
        }

        response = await fetchApi<any>('/api/v1/knowledge/submissions', {
          method: 'POST',
          body: JSON.stringify({
            submitted_by: `${role}-user`,
            submitter_role: role,
            raw_content: content.trim(),
          }),
        })
      } else if (mode === 'file') {
        if (!selectedFile) {
          setError('Please select a document file (.pdf, .docx, .pptx, .txt, .md, .csv, .json).')
          setIsSubmitting(false)
          return
        }

        const formData = new FormData()
        formData.append('file', selectedFile)
        formData.append('submitted_by', `${role}-user`)
        formData.append('submitter_role', role)

        const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
        const res = await fetch(`${baseUrl}/api/v1/knowledge/submissions/file`, {
          method: 'POST',
          body: formData,
        })

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}))
          throw new Error(errData.detail || `File upload failed with status ${res.status}`)
        }
        response = await res.json()
      } else if (mode === 'url') {
        if (!url.trim() || !url.includes('.')) {
          setError('Please enter a valid HTTP/HTTPS URL.')
          setIsSubmitting(false)
          return
        }

        response = await fetchApi<any>('/api/v1/knowledge/submissions/url', {
          method: 'POST',
          body: JSON.stringify({
            submitted_by: `${role}-user`,
            submitter_role: role,
            url: url.trim(),
          }),
        })
      } else if (mode === 'procedure') {
        if (!sopTitle.trim()) {
          setError('Please enter a procedure title.')
          setIsSubmitting(false)
          return
        }
        const validSteps = sopSteps.filter((s) => s.trim().length > 0)
        if (validSteps.length === 0) {
          setError('Please enter at least one operational step.')
          setIsSubmitting(false)
          return
        }

        response = await fetchApi<any>('/api/v1/knowledge/submissions/procedure', {
          method: 'POST',
          body: JSON.stringify({
            submitted_by: `${role}-user`,
            submitter_role: role,
            title: sopTitle.trim(),
            category: sopCategory,
            severity: sopSeverity,
            steps: validSteps,
            notes: sopNotes.trim() || undefined,
          }),
        })
      }

      setResult(response)
      if (mode === 'text') setContent('')
      if (mode === 'file') setSelectedFile(null)
      if (mode === 'url') setUrl('')
      if (mode === 'procedure') {
        setSopTitle('')
        setSopSteps([''])
        setSopNotes('')
      }
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
      <div className="p-6 max-w-4xl mx-auto space-y-6">
        <div className="space-y-1">
          <p className="text-sm text-text-secondary">
            Propose new information for the knowledge base. Select a submission method below.
          </p>
        </div>

        {/* 4 Submission Mode Selector */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 bg-base-800 p-1.5 rounded-sm border border-border">
          <button
            type="button"
            onClick={() => setMode('text')}
            className={`flex items-center justify-center gap-2 py-2 px-3 text-xs font-semibold rounded-sm transition-all ${
              mode === 'text'
                ? 'bg-amber text-base-900 shadow-sm'
                : 'text-text-secondary hover:text-text-primary hover:bg-base-700'
            }`}
          >
            <FileText className="h-3.5 w-3.5" />
            Raw Text
          </button>

          <button
            type="button"
            onClick={() => setMode('file')}
            className={`flex items-center justify-center gap-2 py-2 px-3 text-xs font-semibold rounded-sm transition-all ${
              mode === 'file'
                ? 'bg-amber text-base-900 shadow-sm'
                : 'text-text-secondary hover:text-text-primary hover:bg-base-700'
            }`}
          >
            <Upload className="h-3.5 w-3.5" />
            Document File
          </button>

          <button
            type="button"
            onClick={() => setMode('url')}
            className={`flex items-center justify-center gap-2 py-2 px-3 text-xs font-semibold rounded-sm transition-all ${
              mode === 'url'
                ? 'bg-amber text-base-900 shadow-sm'
                : 'text-text-secondary hover:text-text-primary hover:bg-base-700'
            }`}
          >
            <Link className="h-3.5 w-3.5" />
            Web Link / URL
          </button>

          <button
            type="button"
            onClick={() => setMode('procedure')}
            className={`flex items-center justify-center gap-2 py-2 px-3 text-xs font-semibold rounded-sm transition-all ${
              mode === 'procedure'
                ? 'bg-amber text-base-900 shadow-sm'
                : 'text-text-secondary hover:text-text-primary hover:bg-base-700'
            }`}
          >
            <ListOrdered className="h-3.5 w-3.5" />
            Structured SOP
          </button>
        </div>

        {/* Form Body based on Mode */}
        <form onSubmit={handleSubmit} className="space-y-4 bg-base-800 p-5 border border-border rounded-sm">
          {mode === 'text' && (
            <div className="space-y-2">
              <label className="label-caps block">Raw Text Content</label>
              <textarea
                className="w-full h-44 bg-base-900 border border-border rounded-sm p-3 text-sm text-text-primary focus:border-amber focus:ring-1 focus:ring-amber outline-none resize-y font-sans"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Enter facts, operational rules, or instructions here (min 20 characters)..."
                disabled={isSubmitting}
              />
            </div>
          )}

          {mode === 'file' && (
            <div className="space-y-3">
              <label className="label-caps block">Upload Knowledge Document</label>
              <p className="text-xs text-text-muted">
                Supported formats: PDF (.pdf), Word (.docx), PowerPoint (.pptx), Text (.txt, .md), CSV (.csv), JSON (.json).
              </p>

              <div className="border-2 border-dashed border-border-subtle hover:border-amber rounded-sm p-6 text-center bg-base-900/50 transition-colors">
                <input
                  type="file"
                  id="kb-file-input"
                  className="hidden"
                  accept=".pdf,.docx,.doc,.pptx,.ppt,.txt,.md,.csv,.json"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  disabled={isSubmitting}
                />
                <label htmlFor="kb-file-input" className="cursor-pointer flex flex-col items-center gap-2">
                  <Upload className="h-8 w-8 text-amber" />
                  <span className="text-sm font-semibold text-text-primary">
                    {selectedFile ? selectedFile.name : 'Click to select a file or drag & drop'}
                  </span>
                  {selectedFile && (
                    <span className="text-xs text-text-secondary">
                      {(selectedFile.size / 1024).toFixed(1)} KB — {selectedFile.type || 'Document'}
                    </span>
                  )}
                </label>
              </div>
            </div>
          )}

          {mode === 'url' && (
            <div className="space-y-2">
              <label className="label-caps block">Web Page or Document URL</label>
              <p className="text-xs text-text-muted">
                The system will fetch and extract readable plain text content from the link.
              </p>
              <input
                type="url"
                className="w-full bg-base-900 border border-border rounded-sm p-3 text-sm text-text-primary focus:border-amber focus:ring-1 focus:ring-amber outline-none font-mono"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Paste or type a fact about Dagmawi Teferi (skills, a role, or a project)"
                disabled={isSubmitting}
              />
            </div>
          )}

          {mode === 'procedure' && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="md:col-span-1 space-y-1">
                  <label className="label-caps block">Procedure Title</label>
                  <input
                    type="text"
                    className="w-full bg-base-900 border border-border rounded-sm p-2.5 text-sm text-text-primary focus:border-amber focus:ring-1 outline-none"
                    value={sopTitle}
                    onChange={(e) => setSopTitle(e.target.value)}
                    placeholder="e.g. Auxiliary Generator Shutdown"
                    disabled={isSubmitting}
                  />
                </div>

                <div className="space-y-1">
                  <label className="label-caps block">Category</label>
                  <select
                    className="w-full bg-base-900 border border-border rounded-sm p-2.5 text-sm text-text-primary focus:border-amber focus:ring-1 outline-none"
                    value={sopCategory}
                    onChange={(e) => setSopCategory(e.target.value)}
                    disabled={isSubmitting}
                  >
                    <option value="Engine Operation">Engine Operation</option>
                    <option value="Navigation & Safety">Navigation & Safety</option>
                    <option value="Emergency Protocol">Emergency Protocol</option>
                    <option value="Cargo & Deck">Cargo & Deck</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="label-caps block">Severity Level</label>
                  <select
                    className="w-full bg-base-900 border border-border rounded-sm p-2.5 text-sm text-text-primary focus:border-amber focus:ring-1 outline-none"
                    value={sopSeverity}
                    onChange={(e) => setSopSeverity(e.target.value)}
                    disabled={isSubmitting}
                  >
                    <option value="Routine">Routine</option>
                    <option value="Priority">Priority</option>
                    <option value="Emergency">Emergency</option>
                  </select>
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="label-caps block">Operational Steps</label>
                  <button
                    type="button"
                    onClick={handleAddStep}
                    className="inline-flex items-center gap-1 text-xs text-amber hover:underline"
                  >
                    <Plus className="h-3 w-3" /> Add Step
                  </button>
                </div>

                {sopSteps.map((step, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <span className="text-xs font-mono text-text-secondary w-6">{idx + 1}.</span>
                    <input
                      type="text"
                      className="flex-1 bg-base-900 border border-border rounded-sm p-2 text-sm text-text-primary focus:border-amber outline-none"
                      value={step}
                      onChange={(e) => handleStepChange(idx, e.target.value)}
                      placeholder={`Step ${idx + 1} instruction...`}
                      disabled={isSubmitting}
                    />
                    {sopSteps.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveStep(idx)}
                        className="text-text-muted hover:text-rose p-1"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>

              <div className="space-y-1">
                <label className="label-caps block">Safety Notes & Warnings (Optional)</label>
                <textarea
                  className="w-full h-20 bg-base-900 border border-border rounded-sm p-2.5 text-sm text-text-primary focus:border-amber outline-none resize-y"
                  value={sopNotes}
                  onChange={(e) => setSopNotes(e.target.value)}
                  placeholder="Additional safety precautions or warnings..."
                  disabled={isSubmitting}
                />
              </div>
            </div>
          )}

          {error && (
            <div className="p-3 rounded-sm bg-rose/10 border border-rose/30 text-rose text-sm">
              {error}
            </div>
          )}

          <div className="pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center justify-center gap-2 px-5 py-2.5 bg-amber hover:bg-amber-light text-base-900 rounded-sm text-sm font-bold tracking-tight disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Submit Knowledge ({mode.toUpperCase()})
            </button>
          </div>
        </form>

        {result && (
          <div className="space-y-4 p-5 bg-base-800 border border-border rounded-sm shadow-sm">
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
