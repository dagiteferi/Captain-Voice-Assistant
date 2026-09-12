import { useState, useRef, useEffect } from 'react'
import {
  Terminal,
  Send,
  Mic,
  BookOpen,
  Globe,
  Loader2,
  Sparkles,
  Bot,
  User,
  Trash2,
} from 'lucide-react'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { useRole } from '@/shared/lib/roles'
import { AudioPlayer } from '@/features/audio-player/ui/AudioPlayer'
import { submitCommand, getCommand } from '@/entities/command/api/commandApi'
import type { CommandResponse } from '@/entities/command/model/types'

interface ChatMessage {
  id: string
  sender: 'user' | 'bot'
  text: string
  timestamp: string
  command?: CommandResponse
  isPending?: boolean
  error?: string
}

export function ConsolePage() {
  const { role } = useRole()
  const [inputText, setInputText] = useState('')
  const [targetLanguage, setTargetLanguage] = useState(
    import.meta.env.VITE_DEFAULT_LANGUAGE || 'am'
  )
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [currentStage, setCurrentStage] = useState<number>(-1)
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome-1',
      sender: 'bot',
      text: 'Welcome Captain. I am your RAG-powered Maritime Voice Intelligence Assistant. Ask any operational query or emergency procedure command below.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ])

  const chatEndRef = useRef<HTMLDivElement | null>(null)

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isSubmitting])

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

  const handleSend = async (textToSend?: string) => {
    const text = (textToSend || inputText).trim()
    if (!text || isSubmitting) return

    const userMsgId = `user-${Date.now()}`
    const botMsgId = `bot-${Date.now()}`

    const userMessage: ChatMessage = {
      id: userMsgId,
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    const pendingBotMessage: ChatMessage = {
      id: botMsgId,
      sender: 'bot',
      text: '',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isPending: true,
    }

    setMessages((prev) => [...prev, userMessage, pendingBotMessage])
    if (!textToSend) setInputText('')
    setIsSubmitting(true)
    setCurrentStage(0) // Retrieving

    try {
      const res = await submitCommand(
        {
          input_text: text,
          target_language: targetLanguage,
        },
        role,
      )

      let attempts = 0
      const pollTimer = setInterval(async () => {
        attempts++
        if (attempts <= 3) setCurrentStage(0) // Retrieving
        else if (attempts <= 8) setCurrentStage(1) // Grounding
        else if (attempts <= 15) setCurrentStage(2) // Translating
        else setCurrentStage(3) // Synthesizing

        try {
          const fullCmd = await getCommand(res.command_id, role)
          if (fullCmd.status !== 'pending' || attempts >= 60) {
            clearInterval(pollTimer)
            setIsSubmitting(false)
            setCurrentStage(-1)

            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === botMsgId
                  ? {
                      ...msg,
                      text: fullCmd.answer_text || 'No answer returned by pipeline.',
                      command: fullCmd,
                      isPending: false,
                    }
                  : msg,
              ),
            )
          }
        } catch (err: unknown) {
          if (attempts >= 60) {
            clearInterval(pollTimer)
            setIsSubmitting(false)
            setCurrentStage(-1)

            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === botMsgId
                  ? {
                      ...msg,
                      text: 'Error processing command.',
                      error: err instanceof Error ? err.message : 'Polling failed',
                      isPending: false,
                    }
                  : msg,
              ),
            )
          }
        }
      }, 2000)
    } catch (err: unknown) {
      setIsSubmitting(false)
      setCurrentStage(-1)

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === botMsgId
            ? {
                ...msg,
                text: 'Command submission failed.',
                error: err instanceof Error ? err.message : 'Failed to reach server',
                isPending: false,
              }
            : msg,
        ),
      )
    }
  }

  const stages = ['Retrieving', 'Grounding', 'Translating', 'Synthesizing']

  const presets = [
    'Emergency main engine shutdown procedure',
    'Fuel line pressure check and maintenance',
    'Bilge pump emergency operating steps',
  ]

  return (
    <PageShell
      icon={Terminal}
      title="Command Console"
      label="VOICE & RAG CHAT ASSISTANT"
      badge={<span className="mono text-[11px] px-2 py-0.5 rounded bg-amber/10 border border-amber/30 text-amber font-medium uppercase">{role} ROLE</span>}
    >
      <div className="flex flex-col h-[calc(100vh-140px)] max-w-4xl mx-auto bg-base-900 border border-border rounded-sm shadow-lg overflow-hidden">
        {/* Header / Top Toolbar */}
        <div className="flex items-center justify-between px-4 py-3 bg-base-800 border-b border-border">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-amber" />
            <div>
              <h2 className="text-sm font-semibold text-text-primary">Captain Voice AI Assistant</h2>
              <p className="text-[10px] text-text-muted mono">RAG Pipeline + Translation + Voice Synthesis</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 bg-base-900 px-2.5 py-1 rounded border border-border">
              <Globe className="h-3.5 w-3.5 text-sky" />
              <span className="mono text-xs text-text-secondary">Language:</span>
              <select
                value={targetLanguage}
                onChange={(e) => setTargetLanguage(e.target.value)}
                className="bg-transparent text-xs text-text-primary outline-none cursor-pointer"
                disabled={isSubmitting}
              >
                <option value="am">am — Amharic (አማርኛ)</option>
                <option value="en">en — English</option>
                <option value="fr">fr — French</option>
              </select>
            </div>

            {messages.length > 1 && (
              <button
                onClick={() =>
                  setMessages([
                    {
                      id: 'welcome-1',
                      sender: 'bot',
                      text: 'Welcome Captain. Ask any operational query or emergency procedure command below.',
                      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    },
                  ])
                }
                className="p-1.5 text-text-muted hover:text-rose transition-colors"
                title="Clear Chat History"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>

        {/* Chat Message Scrollable Stream */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-base-900/50">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 max-w-[85%] ${
                msg.sender === 'user' ? 'ml-auto flex-row-reverse' : 'mr-auto'
              }`}
            >
              {/* Avatar Icon */}
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                  msg.sender === 'user'
                    ? 'bg-amber text-base-900'
                    : 'bg-sky/20 border border-sky/40 text-sky'
                }`}
              >
                {msg.sender === 'user' ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
              </div>

              {/* Message Content Bubble */}
              <div className="space-y-2">
                <div
                  className={`p-3.5 rounded-lg text-sm leading-relaxed ${
                    msg.sender === 'user'
                      ? 'bg-amber text-base-900 font-medium rounded-tr-none'
                      : 'bg-base-800 border border-border text-text-primary rounded-tl-none'
                  }`}
                >
                  {msg.isPending ? (
                    <div className="flex items-center gap-2 py-1">
                      <Loader2 className="h-4 w-4 animate-spin text-amber" />
                      <span className="text-xs text-text-secondary">Generating grounded response & voice output...</span>
                    </div>
                  ) : (
                    <p className="whitespace-pre-wrap">{msg.text}</p>
                  )}

                  {msg.error && (
                    <div className="mt-2 p-2 bg-rose/10 border border-rose/30 rounded text-rose text-xs">
                      {msg.error}
                    </div>
                  )}

                  {/* Timestamp */}
                  <div
                    className={`text-[10px] mono mt-1 text-right ${
                      msg.sender === 'user' ? 'text-base-900/70' : 'text-text-muted'
                    }`}
                  >
                    {msg.timestamp}
                  </div>
                </div>

                {/* Extended Details for Bot Message */}
                {msg.command && (
                  <div className="space-y-3 p-3 bg-base-800/80 border border-border rounded-lg text-xs">
                    {/* Citations */}
                    {msg.command.citations && msg.command.citations.length > 0 && (
                      <div className="space-y-1.5">
                        <div className="flex items-center gap-1 text-[11px] font-semibold text-amber">
                          <BookOpen className="h-3.5 w-3.5" />
                          <span>Knowledge Base Citations</span>
                        </div>
                        <div className="grid gap-1.5">
                          {msg.command.citations.map((c) => (
                            <div
                              key={c.chunk_id}
                              className="p-2 bg-base-900 border border-border-subtle rounded flex items-center justify-between text-text-secondary text-[11px]"
                            >
                              <span className="truncate">{c.document_title || `Chunk ${c.chunk_id.slice(0, 8)}`}</span>
                              <span className="mono text-[10px] text-amber">RAG Match</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Translation */}
                    {msg.command.translated_text && (
                      <div className="space-y-1">
                        <div className="flex items-center gap-1 text-[11px] font-semibold text-sky">
                          <Globe className="h-3.5 w-3.5" />
                          <span>Translated Output ({msg.command.target_language.toUpperCase()})</span>
                        </div>
                        <div className="p-2.5 bg-sky/10 border border-sky/20 rounded text-sky leading-relaxed font-sans">
                          {msg.command.translated_text}
                        </div>
                      </div>
                    )}

                    {/* Synthesized Voice Player */}
                    {msg.command.audio_url && (
                      <div className="pt-1">
                        <AudioPlayer
                          audioUrl={msg.command.audio_url}
                          title={`Voice Response (${msg.command.target_language.toUpperCase()})`}
                        />
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          <div ref={chatEndRef} />
        </div>

        {/* Preset Chips (If few messages) */}
        {messages.length <= 2 && (
          <div className="px-4 py-2 bg-base-800/40 border-t border-border-subtle flex flex-wrap gap-2 items-center">
            <span className="text-[11px] text-text-muted mono flex items-center gap-1">
              <Sparkles className="h-3 w-3 text-amber" /> Presets:
            </span>
            {presets.map((preset) => (
              <button
                key={preset}
                onClick={() => handleSend(preset)}
                className="text-xs py-1 px-2.5 bg-base-800 hover:bg-base-700 border border-border rounded text-text-secondary hover:text-text-primary transition-colors text-left"
              >
                {preset}
              </button>
            ))}
          </div>
        )}

        {/* Live Pipeline Execution Progress */}
        {isSubmitting && (
          <div className="px-4 py-2 bg-base-800 border-t border-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 text-sky animate-spin" />
              <span className="mono text-xs text-sky font-semibold">Live Backend Pipeline Active:</span>
            </div>
            <div className="flex items-center gap-3">
              {stages.map((st, idx) => {
                const isDone = idx < currentStage
                const isActive = idx === currentStage
                return (
                  <div key={st} className="flex items-center gap-1">
                    <div
                      className={`w-2 h-2 rounded-full ${
                        isDone ? 'bg-amber' : isActive ? 'bg-sky animate-ping' : 'bg-base-600'
                      }`}
                    />
                    <span
                      className={`mono text-[10px] ${
                        isDone ? 'text-amber' : isActive ? 'text-sky font-bold' : 'text-text-muted'
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

        {/* Fixed Bottom Input Bar */}
        <div className="p-3 bg-base-800 border-t border-border flex items-center gap-2">
          <button
            type="button"
            onClick={() =>
              setInputText('What are the emergency engine shutdown procedures for Vessel Alpha?')
            }
            className="p-2 text-text-muted hover:text-amber transition-colors rounded hover:bg-base-700"
            title="Sample voice command"
          >
            <Mic className="h-4 w-4" />
          </button>

          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Type your command or query here (e.g. 'What is the emergency engine procedure?')..."
            className="flex-1 bg-base-900 border border-border rounded p-2.5 text-sm text-text-primary focus:border-amber focus:ring-1 focus:ring-amber outline-none"
            disabled={isSubmitting}
          />

          <button
            type="button"
            onClick={() => handleSend()}
            disabled={!inputText.trim() || isSubmitting}
            className="btn-primary py-2.5 px-4"
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>
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
