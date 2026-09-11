import { fetchApi } from '@/shared/api/client'
import type {
  BulkDocumentItem,
  BulkIngestResponse,
  KnowledgeSubmissionRequest,
  KnowledgeSubmissionResponse,
  SubmissionItem,
} from '../model/types'

export async function submitKnowledge(
  req: KnowledgeSubmissionRequest,
  role: string,
): Promise<KnowledgeSubmissionResponse> {
  return fetchApi<KnowledgeSubmissionResponse>('/api/v1/knowledge/submissions', {
    method: 'POST',
    body: JSON.stringify(req),
    role,
  })
}

export async function getSubmissions(
  statusFilter?: string,
  role: string = 'captain',
): Promise<{ submissions: SubmissionItem[] }> {
  const query = statusFilter && statusFilter !== 'all' ? `?status=${statusFilter}` : ''
  return fetchApi<{ submissions: SubmissionItem[] }>(`/api/v1/knowledge/submissions${query}`, {
    role,
  })
}

export async function approveSubmission(
  submissionId: string,
  captainId: string,
  role: string = 'captain',
): Promise<{ id: string; status: 'approved'; indexed: boolean }> {
  return fetchApi<{ id: string; status: 'approved'; indexed: boolean }>(
    `/api/v1/knowledge/submissions/${submissionId}/approve`,
    {
      method: 'POST',
      body: JSON.stringify({ reviewed_by: captainId }),
      role,
    },
  )
}

export async function rejectSubmission(
  submissionId: string,
  captainId: string,
  reason?: string,
  role: string = 'captain',
): Promise<{ id: string; status: 'rejected'; reason: string | null }> {
  return fetchApi<{ id: string; status: 'rejected'; reason: string | null }>(
    `/api/v1/knowledge/submissions/${submissionId}/reject`,
    {
      method: 'POST',
      body: JSON.stringify({ reviewed_by: captainId, reason: reason || null }),
      role,
    },
  )
}

export async function bulkIngestDocuments(
  documents: BulkDocumentItem[],
  role: string = 'captain',
): Promise<BulkIngestResponse> {
  return fetchApi<BulkIngestResponse>('/api/v1/knowledge/documents', {
    method: 'POST',
    body: JSON.stringify({ documents }),
    role,
  })
}
