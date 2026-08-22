// author: jf
import { API_BASE_PATH } from './apiBase'
import { fetchWithAuth } from '@/services/authService'

export interface RealtimeClientSecretRequest {
  model?: string
  language?: string
}

export interface RealtimeClientSecretResponse {
  clientSecret?: string
  expiresAt?: number | null
  provider?: 'openai' | 'dashscope'
  model?: string
  language?: string
  realtimeApiBaseUrl?: string
  realtimeCallsPath?: string
  websocketPath?: string
  sampleRate?: number | null
}

export function getRealtimeClientSecretEndpoint(): string {
  return `${API_BASE_PATH}/ai/realtime/client-secret`
}

export async function postRealtimeClientSecret(
  payload: RealtimeClientSecretRequest = {},
  signal?: AbortSignal
): Promise<Response> {
  return fetchWithAuth(getRealtimeClientSecretEndpoint(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  })
}

export async function postRealtimeCallSdp(
  endpoint: string,
  clientSecret: string,
  sdpOffer: string,
  signal?: AbortSignal
): Promise<Response> {
  return fetch(endpoint, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${clientSecret}`,
      'Content-Type': 'application/sdp',
    },
    body: sdpOffer,
    signal,
  })
}
