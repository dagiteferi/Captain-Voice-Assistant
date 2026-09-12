export type CommandStatus = 'pending' | 'grounded' | 'ungrounded' | 'failed'

export interface Citation {
  chunk_id: string
  document_title: string
  similarity_score: number
}

export interface CommandResponse {
  command_id: string
  conversation_id: string
  status: CommandStatus
  input_text: string
  answer_text: string | null
  citations: Citation[]
  translated_text: string | null
  target_language: string
  audio_url: string | null
  fallback_reason: string | null
  created_at: string
  completed_at: string | null
}

export interface TraceEvent {
  event_type:
    | 'RetrievalCompleted'
    | 'AnswerGrounded'
    | 'TranslationCompleted'
    | 'AudioSynthesized'
    | 'PipelineFallback'
  payload: Record<string, unknown>
  occurred_at: string
}

export interface CommandTrace {
  command_id: string
  events: TraceEvent[]
}

export interface SubmitCommandRequest {
  conversation_id?: string | null
  input_text: string
  target_language: string
  voice_id?: string | null
}

export interface SubmitCommandResponse {
  command_id: string
  conversation_id: string
  status: 'pending'
}

export interface ConversationHistory {
  conversation_id: string
  captain_id: string
  target_language: string
  created_at: string
  commands: {
    command_id: string
    input_text: string
    status: string
    created_at: string
  }[]
}
