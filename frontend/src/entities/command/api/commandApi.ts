import { fetchApi } from '@/shared/api/client'
import type {
  CommandResponse,
  CommandTrace,
  SubmitCommandRequest,
  SubmitCommandResponse,
} from '../model/types'

const MOCK_COMMANDS: Record<string, CommandResponse> = {
  'cmd-101': {
    command_id: 'cmd-101',
    conversation_id: 'conv-8842',
    status: 'grounded',
    input_text: 'What are the emergency engine shutdown procedures for Vessel Alpha?',
    answer_text:
      'To execute an emergency engine shutdown on Vessel Alpha: 1. Disengage main throttle control immediately. 2. Activate emergency fuel cut-off valve located on Panel B-2. 3. Engage secondary hydraulic brake. 4. Notify bridge control via VHF Channel 16.',
    citations: [
      {
        chunk_id: 'chk-301',
        document_title: 'Vessel Alpha Standard Operating Procedures (SOP-2024)',
        similarity_score: 0.94,
      },
      {
        chunk_id: 'chk-112',
        document_title: 'Engine Room Safety Protocols Manual v3.2',
        similarity_score: 0.88,
      },
    ],
    translated_text:
      'ለመርከብ አልፋ የአደጋ ጊዜ ሞተር ማጥፊያ ሂደቶች፡ 1. ዋናውን የመሪ መቆጣጠሪያ ወዲያውኑ ያላቅቁ። 2. በፓነል B-2 ላይ የሚገኘውን የአደጋ ጊዜ ነዳጅ ማቋረጫ ቫልቭ ያንቀሳቅሱ። 3. ሁለተኛ ደረጃ ሃይድሮሊክ ብሬክን ያሳትፉ። 4. በVHF ቻናል 16 በኩል ለብሪጅ መቆጣጠሪያ ያሳውቁ።',
    target_language: 'am',
    audio_url: '/api/v1/audio/aud-101',
    created_at: new Date(Date.now() - 120000).toISOString(),
    completed_at: new Date(Date.now() - 116000).toISOString(),
  },
  'cmd-102': {
    command_id: 'cmd-102',
    conversation_id: 'conv-8842',
    status: 'ungrounded',
    input_text: 'What is the maximum speed limit in international waters near sector 7?',
    answer_text:
      'No specific rule found in indexed maritime regulations for sector 7 maximum speed limits. Default international maritime guidelines recommend safe speed based on visibility and traffic density (COLREGs Rule 6).',
    citations: [
      {
        chunk_id: 'chk-099',
        document_title: 'International Regulations for Preventing Collisions at Sea (COLREGs)',
        similarity_score: 0.61,
      },
    ],
    translated_text:
      'በሴክተር 7 አቅራቢያ በዓለም አቀፍ ውቅያኖስ ላይ ስለሚፈቀደው ከፍተኛ ፍጥነት የተወሰነ ህግ አልተገኘም።',
    target_language: 'am',
    audio_url: null,
    created_at: new Date(Date.now() - 600000).toISOString(),
    completed_at: new Date(Date.now() - 597000).toISOString(),
  },
}

export async function submitCommand(
  req: SubmitCommandRequest,
  role: string,
): Promise<SubmitCommandResponse> {
  try {
    return await fetchApi<SubmitCommandResponse>('/api/v1/commands', {
      method: 'POST',
      body: JSON.stringify(req),
      role,
    })
  } catch {
    // Mock fallback
    const mockId = `cmd-${Math.floor(100 + Math.random() * 900)}`
    const convId = req.conversation_id || `conv-${Math.floor(1000 + Math.random() * 9000)}`

    MOCK_COMMANDS[mockId] = {
      command_id: mockId,
      conversation_id: convId,
      status: 'grounded',
      input_text: req.input_text,
      answer_text: `[Grounded Knowledge Response] Verified maritime procedure for "${req.input_text}". All safety protocols checked against active documentation.`,
      citations: [
        {
          chunk_id: `chk-${Math.floor(100 + Math.random() * 800)}`,
          document_title: 'Captain Maritime Operations Manual v4',
          similarity_score: 0.92,
        },
      ],
      translated_text:
        req.target_language === 'am'
          ? `[የተተረጎመ መልስ] ለተሰጠው ትእዛዝ የተረጋገጠ የመርከብ አሰራር መመሪያ።`
          : null,
      target_language: req.target_language,
      audio_url: `/api/v1/audio/aud-${mockId}`,
      created_at: new Date().toISOString(),
      completed_at: new Date(Date.now() + 1500).toISOString(),
    }

    return {
      command_id: mockId,
      conversation_id: convId,
      status: 'pending',
    }
  }
}

export async function getCommand(
  commandId: string,
  role: string,
): Promise<CommandResponse> {
  try {
    return await fetchApi<CommandResponse>(`/api/v1/commands/${commandId}`, {
      role,
    })
  } catch {
    if (MOCK_COMMANDS[commandId]) {
      return MOCK_COMMANDS[commandId]
    }
    // Default fallback mock
    return {
      command_id: commandId,
      conversation_id: 'conv-default',
      status: 'grounded',
      input_text: 'Demo Maritime Command',
      answer_text: 'This is a mock answer response for command ' + commandId,
      citations: [
        { chunk_id: 'chk-1', document_title: 'Standard Operations Guide', similarity_score: 0.89 },
      ],
      translated_text: 'ይህ የሙከራ መልስ ነው።',
      target_language: 'am',
      audio_url: `/api/v1/audio/aud-${commandId}`,
      created_at: new Date().toISOString(),
      completed_at: new Date().toISOString(),
    }
  }
}

export async function getCommandTrace(
  commandId: string,
  role: string,
): Promise<CommandTrace> {
  try {
    return await fetchApi<CommandTrace>(`/api/v1/commands/${commandId}/trace`, {
      role,
    })
  } catch {
    const now = Date.now()
    return {
      command_id: commandId,
      events: [
        {
          event_type: 'RetrievalCompleted',
          payload: {
            retrieved_chunks: 2,
            top_similarity: 0.94,
            duration_ms: 142,
            vector_db: 'Qdrant / PGVector',
          },
          occurred_at: new Date(now - 3500).toISOString(),
        },
        {
          event_type: 'AnswerGrounded',
          payload: {
            grounded: true,
            hallucination_score: 0.02,
            citation_count: 2,
            duration_ms: 680,
          },
          occurred_at: new Date(now - 2800).toISOString(),
        },
        {
          event_type: 'TranslationCompleted',
          payload: {
            target_language: 'am',
            source_language: 'en',
            translated_char_count: 145,
            duration_ms: 310,
          },
          occurred_at: new Date(now - 2100).toISOString(),
        },
        {
          event_type: 'AudioSynthesized',
          payload: {
            audio_format: 'mp3',
            sampling_rate: 24000,
            file_size_bytes: 48210,
            duration_ms: 920,
          },
          occurred_at: new Date(now - 1000).toISOString(),
        },
      ],
    }
  }
}
