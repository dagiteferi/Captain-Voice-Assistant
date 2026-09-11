import { useState } from 'react'
import {
  Terminal,
  Send,
  Mic,
  BookOpen,
  Globe,
  Loader2,
  History,
  Sparkles,
} from 'lucide-react'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { useRole } from '@/shared/lib/roles'
import { AudioPlayer } from '@/features/audio-player/ui/AudioPlayer'
import { submitCommand, getCommand } from '@/entities/command/api/commandApi'
import type { CommandResponse } from '@/entities/command/model/types'

export function ConsolePage() {
  const { role } = useRole()
  const [inputText, setInputText] = useState('')
  const [targetLanguage, setTargetLanguage] = useState(
    import.meta.env.VITE_DEFAULT_LANGUAGE || 'am'
  )
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [currentStage, setCurrentStage] = useState<number>(-1)
  const [activeCommand, setActiveCommand] = useState<CommandResponse | null>(null)
  const [historyList, setHistoryList] = useState<CommandResponse[]>([])
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  if (role === 'guest') {
    return (
      <PageShell
        icon={Terminal}
        title="Command Console"
        label="VOICE COMMAND INTERFACE"
        badge={<StatusBadge status="failed" size="sm" />}
      >
        <div className="panel p-8 text-center space-y-3">
          <StatusBadge status="failed" size="sm" />
          <h2 className="text-base font-semibold text-text-primary">Guest Role Access Restricted</h2>
          <p className="text-text-secondary text-sm max-w-md mx-auto">
            Guests cannot submit voice/text commands or view conversation history. Use the top bar switcher to adopt the <strong className="text-sky">Crew</strong> or <strong className="text-amber">Captain</strong> role.
          </p>
        </div>
      </PageShell>
    )
  }

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!inputText.trim() || isSubmitting) return

    setIsSubmitting(true)
    setErrorMsg(null)
    setCurrentStage(0) // Retrieving

    try {
      const res = await submitCommand(
        {
          input_text: inputText.trim(),
          target_language: targetLanguage,
        },
        role,
      )

      // Poll real backend for command completion (2s intervals, up to 60 attempts = 2 min)
      let attempts = 0
      const pollTimer = setInterval(async () => {
        attempts++
        if (attempts <= 3) setCurrentStage(0)  // Retrieving
        else if (attempts <= 8) setCurrentStage(1) // Grounding
        else if (attempts <= 15) setCurrentStage(2) // Translating
        else setCurrentStage(3) // Synthesizing

        try {
          const fullCmd = await getCommand(res.command_id, role)
          if (fullCmd.status !== 'pending' || attempts >= 60) {
            clearInterval(pollTimer)
            setActiveCommand(fullCmd)
            setHistoryList((prev) => [fullCmd, ...prev.filter((c) => c.command_id !== fullCmd.command_id)])
            setIsSubmitting(false)
            setCurrentStage(-1)
            setInputText('')
          }
        } catch (err: unknown) {
          if (attempts >= 60) {
            clearInterval(pollTimer)
            setIsSubmitting(false)
            setCurrentStage(-1)
            setErrorMsg(err instanceof Error ? err.message : 'Polling failed')
          }
        }
      }, 2000)
    } catch (err: unknown) {
      setIsSubmitting(false)
      setCurrentStage(-1)
      setErrorMsg(err instanceof Error ? err.message : 'Command submission failed')
    }
  }

  const stages = ['Retrieving', 'Grounding', 'Translating', 'Synthesizing']

  return (
    <PageShell
      icon={Terminal}
      title="Command Console"
      label="VOICE COMMAND INTERFACE"
      badge={
        activeCommand ? (
          <StatusBadge status={activeCommand.status} size="sm" />
        ) : (
          <StatusBadge status="pending" size="sm" />
        )
      }
    >
      <div className="space-y-4 animate-fade-in">
        {/* Error Alert if real API call fails */}
        {errorMsg && (
          <div className="p-4 rounded-sm bg-rose/10 border border-rose/30 flex items-start gap-3">
            <Sparkles className="h-5 w-5 text-rose flex-shrink-0" />
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-rose">Command Execution Failed</h3>
              <p className="text-xs text-rose/80 font-mono">{errorMsg}</p>
            </div>
          </div>
        )}

        {/* Command Form Panel */}
        <div className="panel p-4 space-y-3 border-l-2 border-l-amber">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-amber" />
              <p className="label-caps">Submit Voice / Text Command</p>
            </div>
            <span className="mono text-[11px] text-text-muted">
              Role Header: <span className="text-amber uppercase font-semibold">{role}</span>
            </span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="relative">
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Ask maritime query or operational command (e.g., 'What are the emergency engine shutdown procedures?')..."
                className="input-field w-full h-24 resize-none pr-12 focus:border-amber transition-all"
                disabled={isSubmitting}
              />
              <button
                type="button"
                onClick={() =>
                  setInputText(
                    'What are the emergency engine shutdown procedures for Vessel Alpha?',
                  )
                }
                className="absolute right-3 top-3 p-1.5 rounded text-text-muted hover:text-amber transition-colors"
                title="Use voice input simulation preset"
              >
                <Mic className="h-4 w-4" />
              </button>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Globe className="h-3.5 w-3.5 text-text-secondary" />
                <span className="mono text-xs text-text-secondary">Target Language:</span>
                <select
                  value={targetLanguage}
                  onChange={(e) => setTargetLanguage(e.target.value)}
                  className="input-field py-1 text-xs"
                  disabled={isSubmitting}
                >
                  <option value="am">am — Amharic (አማርኛ)</option>
                  <option value="en">en — English</option>
                  <option value="fr">fr — French</option>
                </select>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="submit"
                  disabled={!inputText.trim() || isSubmitting}
                  className="btn-primary"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      Executing Pipeline...
                    </>
                  ) : (
                    <>
                      <Send className="h-3.5 w-3.5" />
                      Submit Command
                    </>
                  )}
                </button>
              </div>
            </div>
          </form>

          {/* Pipeline stage tracker during submission */}
          {isSubmitting && (
            <div className="pt-3 border-t border-border-subtle space-y-2">
              <p className="label-caps text-sky">Live Backend Pipeline Execution Active</p>
              <div className="flex items-center justify-between">
                {stages.map((st, idx) => {
                  const isDone = idx < currentStage
                  const isActive = idx === currentStage
                  return (
                    <div key={st} className="flex items-center gap-1.5">
                      <div
                        className={`w-2.5 h-2.5 rounded-full ${
                          isDone
                            ? 'bg-amber'
                            : isActive
                            ? 'bg-sky animate-ping'
                            : 'bg-base-600'
                        }`}
                      />
                      <span
                        className={`mono text-[11px] ${
                          isDone
                            ? 'text-amber'
                            : isActive
                            ? 'text-sky font-semibold'
                            : 'text-text-muted'
                        }`}
                      >
                        {st}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>

        {/* Active Response Display */}
        {activeCommand ? (
          <div className="panel p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-border">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="mono text-xs text-text-muted font-mono">
                    ID: {activeCommand.command_id}
                  </span>
                  <StatusBadge status={activeCommand.status} />
                </div>
                <h2 className="text-base font-semibold text-text-primary">
                  "{activeCommand.input_text}"
                </h2>
              </div>
              <span className="mono text-[11px] text-text-muted">
                {new Date(activeCommand.created_at).toLocaleTimeString()}
              </span>
            </div>

            {/* Answer Text */}
            <div className="space-y-2">
              <p className="label-caps">Grounded Response</p>
              <div className="p-3.5 rounded bg-base-900 border border-border text-sm text-text-primary leading-relaxed">
                {activeCommand.answer_text || 'No answer returned by pipeline.'}
              </div>
            </div>

            {/* Citations list */}
            {activeCommand.citations && activeCommand.citations.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-1.5">
                  <BookOpen className="h-3.5 w-3.5 text-amber" />
                  <p className="label-caps">Knowledge Base Citations</p>
                </div>
                <div className="grid gap-2 sm:grid-cols-2">
                  {activeCommand.citations.map((c) => (
                    <div
                      key={c.chunk_id}
                      className="p-2.5 rounded bg-base-800 border border-border-subtle flex items-start justify-between gap-2"
                    >
                      <div className="space-y-0.5 min-w-0">
                        <p className="text-xs font-medium text-text-primary truncate">
                          {c.document_title}
                        </p>
                        <p className="mono text-[10px] text-text-muted">
                          Chunk: {c.chunk_id}
                        </p>
                      </div>
                      <span className="mono text-[11px] px-1.5 py-0.5 rounded bg-amber/10 border border-amber/30 text-amber font-medium">
                        {c.similarity_score != null ? `${(c.similarity_score * 100).toFixed(0)}%` : '–'} sim
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Translation output */}
            {activeCommand.translated_text && (
              <div className="space-y-2">
                <div className="flex items-center gap-1.5">
                  <Globe className="h-3.5 w-3.5 text-sky" />
                  <p className="label-caps">Translated Output ({activeCommand.target_language})</p>
                </div>
                <div className="p-3 rounded bg-base-800/80 border border-sky/30 text-sm text-sky font-medium leading-relaxed">
                  {activeCommand.translated_text}
                </div>
              </div>
            )}

            {/* Synthesized Audio Player */}
            <div className="pt-2">
              <AudioPlayer
                audioUrl={activeCommand.audio_url}
                title={`Synthesized Response (${activeCommand.target_language.toUpperCase()})`}
              />
            </div>
          </div>
        ) : (
          <div className="panel p-12 text-center border border-dashed border-border-subtle bg-base-800/50 flex flex-col items-center justify-center gap-3">
            <Terminal className="h-8 w-8 text-text-muted" />
            <p className="text-text-muted text-sm font-medium">No command executed yet</p>
            <p className="text-text-secondary text-xs max-w-sm">Submit a command above to see the real backend response and knowledge citations.</p>
          </div>
        )}

        {/* History List */}
        {historyList.length > 0 && (
          <div className="panel p-4 space-y-3">
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-text-secondary" />
              <p className="label-caps">Session Command History</p>
            </div>

            <div className="divide-y divide-border-subtle">
              {historyList.map((item) => (
                <div
                  key={item.command_id}
                  onClick={() => setActiveCommand(item)}
                  className={`py-2.5 px-2 rounded cursor-pointer transition-colors flex items-center justify-between gap-3 ${
                    activeCommand?.command_id === item.command_id
                      ? 'bg-base-700/60'
                      : 'hover:bg-base-800'
                  }`}
                >
                  <div className="space-y-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="mono text-[11px] text-text-muted">{item.command_id}</span>
                      <StatusBadge status={item.status} size="sm" />
                    </div>
                    <p className="text-xs text-text-primary truncate font-medium">
                      {item.input_text}
                    </p>
                  </div>
                  <span className="mono text-[10px] text-text-muted whitespace-nowrap">
                    {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </PageShell>
  )
}

interface PageShellProps {
  icon: React.ComponentType<{ className?: string }>
  title: string
  label: string
  badge?: React.ReactNode
  children: React.ReactNode
}

export function PageShell({ icon: Icon, title, label, badge, children }: PageShellProps) {
  return (
    <div className="p-4 space-y-4 max-w-4xl mx-auto">
      <div className="flex items-center justify-between py-2 border-b border-border-subtle">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-text-secondary" />
          <h1 className="text-sm font-semibold text-text-primary">{title}</h1>
          <span className="label-caps">{label}</span>
        </div>
        {badge}
      </div>
      {children}
    </div>
  )
}
