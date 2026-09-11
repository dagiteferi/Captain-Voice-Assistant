import { fetchApi } from '@/shared/api/client'
import type {
  CommandResponse,
  CommandTrace,
  SubmitCommandRequest,
  SubmitCommandResponse,
} from '../model/types'

export async function submitCommand(
  req: SubmitCommandRequest,
  role: string,
): Promise<SubmitCommandResponse> {
  return fetchApi<SubmitCommandResponse>('/api/v1/commands', {
    method: 'POST',
    body: JSON.stringify(req),
    role,
  })
}

export async function getCommand(
  commandId: string,
  role: string,
): Promise<CommandResponse> {
  return fetchApi<CommandResponse>(`/api/v1/commands/${commandId}`, {
    role,
  })
}

export async function getCommandTrace(
  commandId: string,
  role: string,
): Promise<CommandTrace> {
  return fetchApi<CommandTrace>(`/api/v1/commands/${commandId}/trace`, {
    role,
  })
}
