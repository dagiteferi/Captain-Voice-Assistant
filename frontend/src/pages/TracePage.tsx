import { useState, useEffect } from 'react'
import { GitBranch, Clock, Radio, RefreshCw, ChevronRight, ChevronDown } from 'lucide-react'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { PageShell } from './ConsolePage'
import { useRole } from '@/shared/lib/roles'
import { getCommandTrace } from '@/entities/command/api/commandApi'
import type { TraceEvent } from '@/entities/command/model/types'

export function TracePage() {
  const { role } = useRole()
  const [selectedCommandId, setSelectedCommandId] = useState('cmd-101')
  const [events, setEvents] = useState<TraceEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedIndices, setExpandedIndices] = useState<Record<number, boolean>>({ 0: true, 1: true })
  const [isLiveStreaming, setIsLiveStreaming] = useState(false)

  const loadTrace = async (cmdId: string) => {
    setLoading(true)
    try {
      const data = await getCommandTrace(cmdId, role)
      setEvents(data.events)
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to fetch trace log')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTrace(selectedCommandId)
  }, [selectedCommandId, role])

  const toggleExpand = (idx: number) => {
    setExpandedIndices((prev) => ({ ...prev, [idx]: !prev[idx] }))
  }

  if (role === 'guest') {
    return (
      <PageShell
        icon={GitBranch}
        title="Pipeline Trace Log"
        label="STAGE & EVENT DIAGNOSTICS"
        badge={<StatusBadge status="failed" size="sm" />}
      >
        <div className="panel p-8 text-center space-y-3">
          <StatusBadge status="failed" size="sm" />
          <h2 className="text-base font-semibold text-text-primary">Guest Role Access Restricted</h2>
          <p className="text-text-secondary text-sm max-w-md mx-auto">
            Guests cannot access pipeline trace diagnostics or event streams. Switch to <strong className="text-sky">Crew</strong> or <strong className="text-amber">Captain</strong> role.
          </p>
        </div>
      </PageShell>
    )
  }

  return (
    <PageShell
      icon={GitBranch}
      title="Pipeline Trace Log"
      label="STAGE & EVENT DIAGNOSTICS"
      badge={
        <div className="flex items-center gap-1.5 text-emerald">
          <Radio className="h-3.5 w-3.5 animate-pulse" />
          <span className="mono text-xs">SSE ACTIVE</span>
        </div>
      }
    >
      <div className="space-y-4 animate-fade-in">
        {/* Controls Bar */}
        <div className="panel p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-base-800">
          <div className="flex items-center gap-3">
            <span className="mono text-xs text-text-secondary">Select Command:</span>
            <select
              value={selectedCommandId}
              onChange={(e) => setSelectedCommandId(e.target.value)}
              className="input-field text-xs font-mono py-1"
            >
              <option value="cmd-101">cmd-101 (Emergency Engine Shutdown)</option>
              <option value="cmd-102">cmd-102 (Sector 7 Speed Limit)</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsLiveStreaming(!isLiveStreaming)}
              className={`btn-secondary text-xs ${isLiveStreaming ? 'border-emerald text-emerald bg-emerald/10' : ''}`}
            >
              <Radio className={`h-3 w-3 ${isLiveStreaming ? 'animate-spin' : ''}`} />
              {isLiveStreaming ? 'Streaming Event Log (SSE)...' : 'Connect SSE Stream'}
            </button>
            <button
              onClick={() => loadTrace(selectedCommandId)}
              disabled={loading}
              className="btn-secondary text-xs"
              title="Refresh Trace Events"
            >
              <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>

        {/* Timeline Events List */}
        <div className="panel p-4 space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-2">
            <p className="label-caps">Execution Event Log ({events.length} Stage Events)</p>
            <span className="mono text-[10px] text-text-muted">Target ID: {selectedCommandId}</span>
          </div>

          <div className="relative border-l border-border ml-3 space-y-4 pl-4 py-1">
            {events.map((event, idx) => {
              const isExpanded = !!expandedIndices[idx]
              const isFallback = event.event_type === 'PipelineFallback'

              return (
                <div key={idx} className="relative group">
                  {/* Event Marker */}
                  <div
                    className={`absolute -left-[21px] top-1.5 w-2.5 h-2.5 rounded-full border-2 ${
                      isFallback
                        ? 'border-rose bg-rose'
                        : 'border-amber bg-base-900 group-hover:bg-amber transition-colors'
                    }`}
                  />

                  <div className="panel p-3 bg-base-800/80 border border-border space-y-2">
                    {/* Header */}
                    <div
                      onClick={() => toggleExpand(idx)}
                      className="flex items-center justify-between cursor-pointer select-none"
                    >
                      <div className="flex items-center gap-2">
                        {isExpanded ? (
                          <ChevronDown className="h-3.5 w-3.5 text-text-secondary" />
                        ) : (
                          <ChevronRight className="h-3.5 w-3.5 text-text-secondary" />
                        )}
                        <span className="mono text-xs font-semibold text-amber">
                          {event.event_type}
                        </span>
                      </div>

                      <div className="flex items-center gap-2">
                        <Clock className="h-3 w-3 text-text-muted" />
                        <span className="mono text-[10px] text-text-muted">
                          {new Date(event.occurred_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                            second: '2-digit',
                          })}
                        </span>
                      </div>
                    </div>

                    {/* Expandable JSON Payload */}
                    {isExpanded && (
                      <div className="pt-2 border-t border-border-subtle space-y-1.5 animate-fade-in">
                        <p className="label-caps text-[10px] text-text-muted">Stage Payload Data</p>
                        <pre className="p-3 rounded bg-base-900 border border-border text-[11px] mono text-sky overflow-x-auto">
                          {JSON.stringify(event.payload, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </PageShell>
  )
}
