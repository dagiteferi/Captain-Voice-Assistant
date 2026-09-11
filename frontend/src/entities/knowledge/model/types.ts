export type SubmissionStatus = 'pending' | 'approved' | 'rejected' | 'indexed'

export interface RuleResult {
  rule:
    | 'MinMaxLengthRule'
    | 'BlocklistKeywordRule'
    | 'DuplicateSimilarityRule'
    | 'TrustedRoleAutoApproveRule'
    | string
  outcome: 'pass' | 'fail'
  similarity?: number
  details?: string
}

export interface KnowledgeSubmissionRequest {
  submitted_by: string
  submitter_role: 'captain' | 'crew' | 'guest'
  raw_content: string
}

export interface KnowledgeSubmissionResponse {
  submission_id: string
  status: SubmissionStatus
  rule_results: RuleResult[]
}

export interface SubmissionItem {
  id: string
  submitted_by: string
  submitter_role: 'captain' | 'crew' | 'guest'
  raw_content: string
  status: SubmissionStatus
  created_at: string
  reviewed_by?: string | null
  rule_results?: RuleResult[]
}

export interface BulkDocumentItem {
  title: string
  content: string
}

export interface BulkIngestResponse {
  ingested_count: number
  document_ids: string[]
}
