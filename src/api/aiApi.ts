// author: jf
import { API_BASE_PATH } from './apiBase'
import { fetchWithAuth } from '@/services/authService'

export interface ChatRequestPayload {
  message: string
  sanitizeOutput?: boolean
}

export interface ChatResponsePayload {
  answer?: string
}

export function getAiChatEndpoint(): string {
  return `${API_BASE_PATH}/ai/chat`
}

export function getAiChatStreamEndpoint(): string {
  return `${API_BASE_PATH}/ai/chat/stream`
}

export async function postAiChat(
  requestBody: ChatRequestPayload,
  signal?: AbortSignal
): Promise<Response> {
  return fetchWithAuth(getAiChatEndpoint(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(requestBody),
    signal,
  })
}

export async function postAiChatStream(
  requestBody: ChatRequestPayload,
  signal?: AbortSignal
): Promise<Response> {
  return fetchWithAuth(getAiChatStreamEndpoint(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
    },
    body: JSON.stringify(requestBody),
    signal,
  })
}
