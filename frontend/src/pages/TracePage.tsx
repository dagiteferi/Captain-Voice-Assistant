import { useState, useEffect } from 'react'
import { GitBranch, Clock, Radio, RefreshCw, ChevronRight, ChevronDown, Search } from 'lucide-react'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { PageShell } from './ConsolePage'
import { useRole } from '@/shared/lib/roles'
import { getCommandTrace, getRecentCommands } from '@/entities/command/api/commandApi'
import type { TraceEvent } from '@/entities/command/model/types'

export function TracePage() {
  const { role } = useRole()
  const [selectedCommandId, setSelectedCommandId] = useState('')
  const [recentCommands, setRecentCommands] = useState<Array<{ command_id: string; input_text: string; status: string; created_at: string }>>([])
  const [events, setEvents] = useState<TraceEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [expandedIndices, setExpandedIndices] = useState<Record<number, boolean>>({ 0: true, 1: true })
  const [isLiveStreaming, setIsLiveStreaming] = useState(false)

  useEffect(() => {
    if (role === 'guest') return
    getRecentCommands(role).then((cmds) => {
      setRecentCommands(cmds)
      if (cmds.length > 0 && !selectedCommandId) {
        setSelectedCommandId(cmds[0].command_id)
      }
    })
  }, [role])

  const loadTrace = async (cmdId: string) => {
    if (!cmdId || !cmdId.trim()) {
      setEvents([])
      return
    }
    setLoading(true)
    setErrorMsg(null)
    try {
      const data = await getCommandTrace(cmdId, role)
      setEvents(data.events || [])
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Failed to fetch trace log')
      setEvents([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (selectedCommandId) {
      loadTrace(selectedCommandId)
    }
  }, [selectedCommandId, role])


  useEffect(() => {
    if (!isLiveStreaming || !selectedCommandId.trim()) return

    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    let eventSource: EventSource | null = null
    let reconnectTimeout: ReturnType<typeof setTimeout>
    let lastEventId: string | undefined = undefined

    const connect = () => {
      let url = `${baseUrl}/api/v1/commands/${selectedCommandId}/stream`
      if (lastEventId) {
        url += `?since_event_id=${lastEventId}`
      }

      eventSource = new EventSource(url)

      eventSource.onmessage = (event) => {
        if (event.lastEventId) {
          lastEventId = event.lastEventId
        }
        try {
          const parsed = JSON.parse(event.data)
          if (parsed.id) lastEventId = parsed.id

          setEvents(prev => {
            if (prev.some(e => e.occurred_at === parsed.occurred_at && e.event_type === parsed.event_type)) {
              return prev
            }
            return [...prev, parsed]
          })
        } catch (e) {
          console.error('SSE Parse error', e)
        }
      }

      eventSource.onerror = () => {
        eventSource?.close()
        reconnectTimeout = setTimeout(() => connect(), 3000)
      }
    }

    connect()

    return () => {
      clearTimeout(reconnectTimeout)
      if (eventSource) {
        eventSource.close()
      }
    }
  }, [isLiveStreaming, selectedCommandId])

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
    >
      <div className="space-y-4 animate-fade-in">
        {/* Controls Bar */}
        <div className="panel p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-base-800">
          <div className="flex flex-wrap items-center gap-2 flex-1">
            {recentCommands.length > 0 && (
              <select
                value={selectedCommandId}
                onChange={(e) => setSelectedCommandId(e.target.value)}
                className="bg-base-900 border border-border text-xs text-text-primary px-2.5 py-1.5 rounded font-mono outline-none max-w-[220px] truncate"
              >
                <option value="">Select Command...</option>
                {recentCommands.map((cmd) => (
                  <option key={cmd.command_id} value={cmd.command_id}>
                    {cmd.input_text ? (cmd.input_text.length > 25 ? cmd.input_text.substring(0, 22) + '...' : cmd.input_text) : cmd.command_id}
                  </option>
                ))}
              </select>
            )}

            <div className="flex items-center gap-2 flex-1 max-w-sm">
              <Search className="h-3.5 w-3.5 text-text-muted" />
              <input
                type="text"
                value={selectedCommandId}
                onChange={(e) => setSelectedCommandId(e.target.value)}
                placeholder="Enter Command ID UUID..."
                className="input-field text-xs font-mono py-1 flex-1"
              />
              <button
                onClick={() => loadTrace(selectedCommandId)}
                className="btn-primary text-xs py-1"
              >
                Fetch Trace
              </button>
            </div>
          </div>


          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsLiveStreaming(!isLiveStreaming)}
              className={`btn-secondary text-xs ${isLiveStreaming ? 'border-emerald text-emerald bg-emerald/10' : ''}`}
            >
              <Radio className={`h-3 w-3 ${isLiveStreaming ? 'animate-spin' : ''}`} />
              {isLiveStreaming ? 'Streaming SSE Event Log...' : 'Connect SSE Stream'}
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

        {/* Error Notification */}
        {errorMsg && (
          <div className="p-3.5 rounded bg-rose/10 border border-rose/30 text-rose text-xs font-mono">
            <strong>Backend Error ({selectedCommandId}):</strong> {errorMsg}
          </div>
        )}

        {/* Timeline Events List */}
        <div className="panel p-4 space-y-4">
          <div className="flex items-center justify-between border-b border-border-subtle pb-2">
            <p className="label-caps">Execution Event Log ({events.length} Stage Events)</p>
            <span className="mono text-[10px] text-text-muted">Command ID: {selectedCommandId}</span>
          </div>

          {events.length === 0 && !errorMsg ? (
            <div className="p-6 text-center text-text-muted text-xs font-mono">
              No trace events found for command ID "{selectedCommandId}". Execute a command in the Console page first.
            </div>
          ) : (
            <div className="relative border-l border-border ml-3 space-y-4 pl-4 py-1">
              {events.map((event, idx) => {
                const isExpanded = !!expandedIndices[idx]
                const isFallback = event.event_type === 'PipelineFallback'

                return (
                  <div key={idx} className="relative group">
                    <div
                      className={`absolute -left-[21px] top-1.5 w-2.5 h-2.5 rounded-full border-2 ${
                        isFallback
                          ? 'border-rose bg-rose'
                          : 'border-amber bg-base-900 group-hover:bg-amber transition-colors'
                      }`}
                    />

                    <div className="panel p-3 bg-base-800/80 border border-border space-y-2">
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
          )}
        </div>
      </div>
    </PageShell>
  )
}
