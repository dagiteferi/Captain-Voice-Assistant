import { fetchApi } from '@/shared/api/client'
import type {
  BulkDocumentItem,
  BulkIngestResponse,
  KnowledgeSubmissionRequest,
  KnowledgeSubmissionResponse,
  SubmissionItem,
} from '../model/types'

let MOCK_SUBMISSIONS: SubmissionItem[] = [
  {
    id: 'sub-801',
    submitted_by: 'officer-sarah',
    submitter_role: 'crew',
    raw_content:
      'Emergency VHF Channel 16 must be monitored continuously at all times during watch shifts. Relaying auxiliary distress signals is mandatory under IMO Regulation 10.',
    status: 'pending',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    rule_results: [
      { rule: 'MinMaxLengthRule', outcome: 'pass', details: 'Length 158 chars (limit 20–4000)' },
      { rule: 'BlocklistKeywordRule', outcome: 'pass', details: 'No restricted terms detected' },
      { rule: 'DuplicateSimilarityRule', outcome: 'pass', similarity: 0.38, details: 'Max similarity 38%' },
      { rule: 'TrustedRoleAutoApproveRule', outcome: 'pass', details: 'Crew role requires manual captain review' },
    ],
  },
  {
    id: 'sub-802',
    submitted_by: 'guest-visitor-9',
    submitter_role: 'guest',
    raw_content:
      'Port authority contact number for Alexandria anchorage control is +20 3 4800000. Operating hours 08:00 - 18:00 UTC.',
    status: 'pending',
    created_at: new Date(Date.now() - 7200000).toISOString(),
    rule_results: [
      { rule: 'MinMaxLengthRule', outcome: 'pass' },
      { rule: 'BlocklistKeywordRule', outcome: 'pass' },
      { rule: 'DuplicateSimilarityRule', outcome: 'pass', similarity: 0.12 },
      { rule: 'TrustedRoleAutoApproveRule', outcome: 'pass', details: 'Guest submissions always require captain review' },
    ],
  },
  {
    id: 'sub-803',
    submitted_by: 'captain-main',
    submitter_role: 'captain',
    raw_content:
      'Updated fuel transfer procedure for Starboard Tank 3: Check automatic flow sensors before opening valve V-4.',
    status: 'approved',
    reviewed_by: 'captain-main',
    created_at: new Date(Date.now() - 14400000).toISOString(),
    rule_results: [
      { rule: 'MinMaxLengthRule', outcome: 'pass' },
      { rule: 'BlocklistKeywordRule', outcome: 'pass' },
      { rule: 'DuplicateSimilarityRule', outcome: 'pass', similarity: 0.22 },
      { rule: 'TrustedRoleAutoApproveRule', outcome: 'pass', details: 'Captain role auto-approved' },
    ],
  },
  {
    id: 'sub-804',
    submitted_by: 'crew-engineer',
    submitter_role: 'crew',
    raw_content: 'Spam text test 1234567890',
    status: 'rejected',
    reviewed_by: 'system-rule-engine',
    created_at: new Date(Date.now() - 28800000).toISOString(),
    rule_results: [
      { rule: 'MinMaxLengthRule', outcome: 'pass' },
      { rule: 'BlocklistKeywordRule', outcome: 'fail', details: 'Failed low information density check' },
      { rule: 'DuplicateSimilarityRule', outcome: 'pass', similarity: 0.05 },
      { rule: 'TrustedRoleAutoApproveRule', outcome: 'fail' },
    ],
  },
]

export async function submitKnowledge(
  req: KnowledgeSubmissionRequest,
  role: string,
): Promise<KnowledgeSubmissionResponse> {
  try {
    return await fetchApi<KnowledgeSubmissionResponse>(
      '/api/v1/knowledge/submissions',
      {
        method: 'POST',
        body: JSON.stringify(req),
        role,
      },
    )
  } catch {
    // Mock rule evaluation logic
    const len = req.raw_content.trim().length
    const lenPass = len >= 20 && len <= 4000
    const isBlocklisted = req.raw_content.toLowerCase().includes('spam') || req.raw_content.toLowerCase().includes('hack')
    const simScore = Math.random() * 0.5

    const rule_results = [
      {
        rule: 'MinMaxLengthRule',
        outcome: (lenPass ? 'pass' : 'fail') as 'pass' | 'fail',
        details: lenPass ? `Length ${len} chars (20–4000)` : `Length ${len} chars out of bounds`,
      },
      {
        rule: 'BlocklistKeywordRule',
        outcome: (isBlocklisted ? 'fail' : 'pass') as 'pass' | 'fail',
        details: isBlocklisted ? 'Restricted keyword detected' : 'Clean content',
      },
      {
        rule: 'DuplicateSimilarityRule',
        outcome: (simScore < 0.85 ? 'pass' : 'fail') as 'pass' | 'fail',
        similarity: parseFloat(simScore.toFixed(2)),
        details: `Max similarity ${(simScore * 100).toFixed(0)}%`,
      },
      {
        rule: 'TrustedRoleAutoApproveRule',
        outcome: 'pass' as const,
        details: req.submitter_role === 'captain' ? 'Auto-approved for Captain' : 'Requires review',
      },
    ]

    let status: 'pending' | 'approved' | 'rejected' = 'pending'
    if (!lenPass || isBlocklisted || simScore >= 0.85) {
      status = 'rejected'
    } else if (req.submitter_role === 'captain') {
      status = 'approved'
    } else {
      status = 'pending'
    }

    const subId = `sub-${Math.floor(800 + Math.random() * 200)}`
    const newItem: SubmissionItem = {
      id: subId,
      submitted_by: req.submitted_by,
      submitter_role: req.submitter_role,
      raw_content: req.raw_content,
      status,
      created_at: new Date().toISOString(),
      rule_results,
    }

    MOCK_SUBMISSIONS.unshift(newItem)

    return {
      submission_id: subId,
      status,
      rule_results,
    }
  }
}

export async function getSubmissions(
  statusFilter?: string,
  role: string = 'captain',
): Promise<{ submissions: SubmissionItem[] }> {
  try {
    const query = statusFilter ? `?status=${statusFilter}` : ''
    return await fetchApi<{ submissions: SubmissionItem[] }>(
      `/api/v1/knowledge/submissions${query}`,
      { role },
    )
  } catch {
    let list = MOCK_SUBMISSIONS
    if (statusFilter && statusFilter !== 'all') {
      list = list.filter((s) => s.status === statusFilter)
    }
    return { submissions: list }
  }
}

export async function approveSubmission(
  submissionId: string,
  captainId: string,
  role: string = 'captain',
): Promise<{ id: string; status: 'approved'; indexed: boolean }> {
  try {
    return await fetchApi<{ id: string; status: 'approved'; indexed: boolean }>(
      `/api/v1/knowledge/submissions/${submissionId}/approve`,
      {
        method: 'POST',
        body: JSON.stringify({ reviewed_by: captainId }),
        role,
      },
    )
  } catch {
    MOCK_SUBMISSIONS = MOCK_SUBMISSIONS.map((s) =>
      s.id === submissionId
        ? { ...s, status: 'approved', reviewed_by: captainId }
        : s,
    )
    return { id: submissionId, status: 'approved', indexed: true }
  }
}

export async function rejectSubmission(
  submissionId: string,
  captainId: string,
  reason?: string,
  role: string = 'captain',
): Promise<{ id: string; status: 'rejected'; reason: string | null }> {
  try {
    return await fetchApi<{ id: string; status: 'rejected'; reason: string | null }>(
      `/api/v1/knowledge/submissions/${submissionId}/reject`,
      {
        method: 'POST',
        body: JSON.stringify({ reviewed_by: captainId, reason }),
        role,
      },
    )
  } catch {
    MOCK_SUBMISSIONS = MOCK_SUBMISSIONS.map((s) =>
      s.id === submissionId
        ? { ...s, status: 'rejected', reviewed_by: captainId }
        : s,
    )
    return { id: submissionId, status: 'rejected', reason: reason || null }
  }
}

export async function bulkIngestDocuments(
  documents: BulkDocumentItem[],
  role: string = 'captain',
): Promise<BulkIngestResponse> {
  try {
    return await fetchApi<BulkIngestResponse>('/api/v1/knowledge/documents', {
      method: 'POST',
      body: JSON.stringify({ documents }),
      role,
    })
  } catch {
    return {
      ingested_count: documents.length,
      document_ids: documents.map((_, i) => `doc-${Date.now()}-${i}`),
    }
  }
}
