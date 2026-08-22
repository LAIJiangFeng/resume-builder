// author: jf
import { API_BASE_PATH } from './apiBase'
import { fetchWithAuth } from '@/services/authService'
import type { InterviewTurnRequest } from '@/services/interview/types'

export function getInterviewTurnStreamEndpoint(): string {
  return `${API_BASE_PATH}/ai/interview/turn/stream`
}

export function getInterviewSessionsEndpoint(limit?: number): string {
  const query = typeof limit === 'number' && Number.isFinite(limit) ? `?limit=${Math.max(1, Math.floor(limit))}` : ''
  return `${API_BASE_PATH}/ai/interview/sessions${query}`
}

export function getInterviewSessionDetailEndpoint(sessionId: string): string {
  return `${API_BASE_PATH}/ai/interview/sessions/${encodeURIComponent(sessionId)}`
}

export async function postInterviewTurnStream(
  requestBody: InterviewTurnRequest,
  signal?: AbortSignal
): Promise<Response> {
  return fetchWithAuth(getInterviewTurnStreamEndpoint(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/x-ndjson',
    },
    body: JSON.stringify(requestBody),
    signal,
  })
}

export async function getInterviewSessions(limit = 20, signal?: AbortSignal): Promise<Response> {
  return fetchWithAuth(getInterviewSessionsEndpoint(limit), {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    signal,
  })
}

export async function getInterviewSessionDetail(sessionId: string, signal?: AbortSignal): Promise<Response> {
  return fetchWithAuth(getInterviewSessionDetailEndpoint(sessionId), {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    signal,
  })
}
