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
  Play,
  Square,
} from 'lucide-react'
import { StatusBadge } from '@/shared/ui/StatusBadge'
import { useRole } from '@/shared/lib/roles'
import { useSettings, voiceForLanguage } from '@/shared/lib/useSettings'
import { useAudioBlob } from '@/shared/api/useAudioBlob'
import { submitCommand, getCommand, retranslateCommand, getKnowledgePresets } from '@/entities/command/api/commandApi'
import type { CommandResponse } from '@/entities/command/model/types'

function withCacheBust(url: string | null | undefined): string | null {
  if (!url) return null
  const separator = url.includes('?') ? '&' : '?'
  return `${url}${separator}t=${Date.now()}`
}

function displayText(command: CommandResponse): string {
  const text = command.translated_text || command.answer_text
  if (text) return text
  if (command.status === 'ungrounded' || command.status === 'failed') {
    return 'No grounded answer was found in the knowledge base. Add the fact in Knowledge, wait until it is Indexed, then ask again.'
  }
  return 'The assistant is still working, or the language model did not return text. Try the same question once more.'
}

interface ChatMessage {
  id: string
  sender: 'user' | 'bot'
  text: string
  timestamp: string
  command?: CommandResponse
  isPending?: boolean
  error?: string
}

function welcomeMessage(): ChatMessage {
  return {
    id: 'welcome-1',
    sender: 'bot',
    text: 'Welcome Captain. I am a RAG-powered voice assistant grounded in Dagmawi Teferi’s professional knowledge base. Ask about his skills, experience, or projects.',
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  }
}

let persistedMessages: ChatMessage[] | null = null
let appliedVoices = { am: '', en: '' }

export function ConsolePage() {
  const { role } = useRole()
  const { settings } = useSettings()
  
  const [inputText, setInputText] = useState('')
  const [targetLanguage, setTargetLanguage] = useState(
    settings.defaultLanguage || import.meta.env.VITE_DEFAULT_LANGUAGE || 'am'
  )
  
  useEffect(() => {
    setTargetLanguage(settings.defaultLanguage)
  }, [settings.defaultLanguage])

  const [isSubmitting, setIsSubmitting] = useState(false)
  const [currentStage, setCurrentStage] = useState<number>(-1)
  const [busyMsgId, setBusyMsgId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>(() => persistedMessages ?? [welcomeMessage()])

  const chatEndRef = useRef<HTMLDivElement | null>(null)

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isSubmitting])

  useEffect(() => {
    persistedMessages = messages
  }, [messages])

  const [presets, setPresets] = useState<string[]>([])

  useEffect(() => {
    getKnowledgePresets(role).then((dynamicPresets) => {
      if (dynamicPresets && dynamicPresets.length > 0) {
        setPresets(dynamicPresets)
        const topTopics = dynamicPresets.slice(0, 3).join(', ')
        const dynamicWelcome = `Welcome Captain. I am your RAG-powered Voice Intelligence Assistant grounded in Dagmawi Teferi's profile. Try asking about: ${topTopics}.`
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === 'welcome-1' ? { ...msg, text: dynamicWelcome } : msg
          )
        )
      }
    })
  }, [role])



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
          voice_id: voiceForLanguage(settings, targetLanguage),
        },
        role,
      )

      let attempts = 0
      const pollTimer = setInterval(async () => {
        attempts++
        if (attempts <= 4) setCurrentStage(0)
        else if (attempts <= 10) setCurrentStage(1)
        else if (attempts <= 16) setCurrentStage(2)
        else setCurrentStage(3)

        try {
          const fullCmd = await getCommand(res.command_id, role)
          if (fullCmd.status !== 'pending' || attempts >= 80) {
            clearInterval(pollTimer)
            setIsSubmitting(false)
            setCurrentStage(-1)

            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === botMsgId
                  ? {
                      ...msg,
                      text: displayText(fullCmd),
                      command: {
                        ...fullCmd,
                        audio_url: withCacheBust(fullCmd.audio_url),
                      },
                      isPending: false,
                    }
                  : msg,
              ),
            )
          }
        } catch (err: unknown) {
          if (attempts >= 80) {
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
      }, 400)
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

  const handleRetranslate = async (commandId: string, newLang: string, botMsgId: string) => {
    setBusyMsgId(botMsgId)
    try {
      const res = await retranslateCommand(
        commandId,
        newLang,
        role,
        voiceForLanguage(settings, newLang),
      )
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === botMsgId && msg.command
            ? {
                ...msg,
                error: undefined,
                command: {
                  ...msg.command,
                  translated_text: res.translated_text,
                  audio_url: withCacheBust(res.audio_url),
                  target_language: res.target_language,
                },
                text: res.translated_text || msg.text,
              }
            : msg,
        ),
      )
    } catch (e) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === botMsgId
            ? {
                ...msg,
                error: e instanceof Error ? e.message : 'Translation failed. Try again.',
              }
            : msg,
        ),
      )
    } finally {
      setBusyMsgId(null)
    }
  }

  useEffect(() => {
    const changed =
      appliedVoices.am !== settings.voiceIdAm || appliedVoices.en !== settings.voiceIdEn
    appliedVoices = { am: settings.voiceIdAm, en: settings.voiceIdEn }
    if (!changed) return
    const bots = messages.filter((msg) => msg.command && !msg.isPending)
    bots.forEach((msg) => {
      if (msg.command) {
        void handleRetranslate(msg.command.command_id, msg.command.target_language, msg.id)
      }
    })
    // Re-speak existing replies when a settings voice changes (including after returning from Settings).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [settings.voiceIdAm, settings.voiceIdEn])

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

  const stages = ['Retrieving', 'Grounding', 'Translating', 'Synthesizing']


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
                onClick={() => {
                  const topTopics = presets.length > 0 ? presets.slice(0, 3).join(', ') : ''
                  const dynamicText = topTopics
                    ? `Welcome Captain. I am your RAG-powered Voice Intelligence Assistant grounded in: ${topTopics}. Ask any operational query or emergency procedure command below.`
                    : 'Welcome Captain. Ask any operational query or emergency procedure command below.'
                  setMessages([
                    {
                      id: 'welcome-1',
                      sender: 'bot',
                      text: dynamicText,
                      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                    },
                  ])
                }}
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
                  className={`p-3.5 rounded-lg leading-relaxed ${
                    settings.textSize === 'xl' ? 'text-lg' : settings.textSize === 'large' ? 'text-base' : 'text-sm'
                  } ${
                    msg.sender === 'user'
                      ? 'bg-amber text-base-900 font-medium rounded-tr-none'
                      : 'bg-base-800 border border-border text-text-primary rounded-tl-none'
                  }`}
                >
                  {msg.isPending ? (
                    <div className="flex items-center gap-1.5 py-2 px-1">
                      <div className="w-1.5 h-1.5 bg-amber rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-1.5 h-1.5 bg-amber rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-1.5 h-1.5 bg-amber rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
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

                {/* Translate & Audio Controls */}
                {msg.command && (
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1.5 bg-base-800/80 px-2 py-1.5 rounded border border-border">
                      <Globe className="h-3 w-3 text-sky" />
                      <select
                        value={msg.command.target_language}
                        disabled={busyMsgId === msg.id}
                        onChange={(e) => handleRetranslate(msg.command!.command_id, e.target.value, msg.id)}
                        className="bg-transparent text-[11px] font-medium text-text-secondary outline-none cursor-pointer disabled:opacity-50"
                      >
                        <option value="am">Amharic (አማርኛ)</option>
                        <option value="en">English</option>
                      </select>
                    </div>

                    {busyMsgId === msg.id ? (
                      <span className="text-[10px] mono text-sky flex items-center gap-1">
                        <Loader2 className="h-3 w-3 animate-spin" /> Updating…
                      </span>
                    ) : (
                      msg.command.audio_url && (
                        <BotMessageAudio key={msg.command.audio_url} audioUrl={msg.command.audio_url} autoPlay={settings.autoPlayVoice} />
                      )
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}

          <div ref={chatEndRef} />
        </div>


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
              setInputText(presets.length > 0 ? presets[0] : 'Who is Dagmawi Teferi and what does he do?')
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

function BotMessageAudio({ audioUrl, autoPlay }: { audioUrl: string, autoPlay: boolean }) {
  const { blobUrl } = useAudioBlob(audioUrl)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)

  useEffect(() => {
    if (blobUrl && audioRef.current && autoPlay) {
      audioRef.current.play().then(() => {
        setIsPlaying(true)
      }).catch((e) => console.error("Auto-play failed:", e))
    }
  }, [blobUrl, autoPlay])

  if (!blobUrl) return null

  const togglePlay = () => {
    if (!audioRef.current) return
    if (isPlaying) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      setIsPlaying(false)
    } else {
      audioRef.current.play()
      setIsPlaying(true)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <audio
        ref={audioRef}
        src={blobUrl}
        onEnded={() => setIsPlaying(false)}
        onPause={() => setIsPlaying(false)}
        onPlay={() => setIsPlaying(true)}
        className="hidden"
      />
      <button
        onClick={togglePlay}
        className="p-1.5 rounded-full bg-amber text-base-900 hover:bg-amber-dim hover:text-amber transition-colors flex-shrink-0"
        title={isPlaying ? "Stop" : "Play"}
      >
        {isPlaying ? <Square className="h-3 w-3 fill-current" /> : <Play className="h-3 w-3 fill-current ml-0.5" />}
      </button>
      <span className="text-[10px] mono text-amber">Voice Output</span>
    </div>
  )
}
