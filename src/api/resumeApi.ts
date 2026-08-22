// author: jf
import { API_BASE_PATH } from './apiBase'
import { fetchWithAuth } from '@/services/authService'

export interface ResumeWritePayload {
  name?: string
  data?: Record<string, unknown>
}

function resumeEndpoint(resumeId?: string): string {
  return resumeId
    ? `${API_BASE_PATH}/resumes/${encodeURIComponent(resumeId)}`
    : `${API_BASE_PATH}/resumes`
}

function jsonHeaders(): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  }
}

export function getResumes(signal?: AbortSignal): Promise<Response> {
  return fetchWithAuth(resumeEndpoint(), {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal,
  })
}

export function getResume(resumeId: string, signal?: AbortSignal): Promise<Response> {
  return fetchWithAuth(resumeEndpoint(resumeId), {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal,
  })
}

export function postResume(payload: ResumeWritePayload): Promise<Response> {
  return fetchWithAuth(resumeEndpoint(), {
    method: 'POST',
    headers: jsonHeaders(),
    body: JSON.stringify(payload),
  })
}

export function putResume(resumeId: string, payload: ResumeWritePayload): Promise<Response> {
  return fetchWithAuth(resumeEndpoint(resumeId), {
    method: 'PUT',
    headers: jsonHeaders(),
    body: JSON.stringify(payload),
  })
}

export function postActivateResume(resumeId: string): Promise<Response> {
  return fetchWithAuth(`${resumeEndpoint(resumeId)}/activate`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  })
}

export function postDuplicateResume(resumeId: string): Promise<Response> {
  return fetchWithAuth(`${resumeEndpoint(resumeId)}/duplicate`, {
    method: 'POST',
    headers: { Accept: 'application/json' },
  })
}

export function deleteResume(resumeId: string): Promise<Response> {
  return fetchWithAuth(resumeEndpoint(resumeId), {
    method: 'DELETE',
  })
}
