// author: jf
import { API_BASE_PATH } from './apiBase'
import type { AuthRole, AiPermission } from '@/services/authService'

export interface AuthLoginRequestPayload {
  username: string
  keyId: string
  encryptedKey: string
  iv: string
  encryptedPassword: string
  issuedAt: number
  requestId: string
}

export interface AuthLoginKeyResponsePayload {
  algorithm: 'RSA-OAEP-256+A256GCM'
  keyId: string
  publicKey: string
}

export interface AuthRegisterRequestPayload {
  email: string
  verificationCode: string
  password: string
  displayName: string
}

export interface AuthEmailCodeRequestPayload {
  email: string
}

export interface AuthEmailCodeResponsePayload {
  cooldownSeconds: number
  expiresInSeconds: number
}

export interface AuthPasswordResetRequestPayload {
  email: string
  verificationCode: string
  newPassword: string
}

export interface AuthLoginResponsePayload {
  accessToken: string
  user: {
    id: string
    username: string
    displayName: string
    role: AuthRole
    permissions: AiPermission[]
  }
}

export type AuthRegisterResponsePayload = AuthLoginResponsePayload

export function getAuthLoginEndpoint(): string {
  return `${API_BASE_PATH}/auth/login`
}

export function getAuthLoginKeyEndpoint(): string {
  return `${API_BASE_PATH}/auth/login-key`
}

export function getAuthRegisterEndpoint(): string {
  return `${API_BASE_PATH}/auth/register`
}

export function getAuthEmailCodeEndpoint(): string {
  return `${API_BASE_PATH}/auth/email-code`
}

export function getAuthPasswordResetEmailCodeEndpoint(): string {
  return `${API_BASE_PATH}/auth/password-reset/email-code`
}

export function getAuthPasswordResetEndpoint(): string {
  return `${API_BASE_PATH}/auth/password-reset`
}

export async function getAuthLoginKey(signal?: AbortSignal): Promise<Response> {
  return fetch(getAuthLoginKeyEndpoint(), {
    method: 'GET',
    headers: {
      Accept: 'application/json',
    },
    cache: 'no-store',
    signal,
  })
}

export async function postAuthLogin(payload: AuthLoginRequestPayload, signal?: AbortSignal): Promise<Response> {
  return fetch(getAuthLoginEndpoint(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  })
}

export async function postAuthRegister(payload: AuthRegisterRequestPayload, signal?: AbortSignal): Promise<Response> {
  return fetch(getAuthRegisterEndpoint(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  })
}

export async function postAuthEmailCode(payload: AuthEmailCodeRequestPayload, signal?: AbortSignal): Promise<Response> {
  return fetch(getAuthEmailCodeEndpoint(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  })
}

export async function postAuthPasswordResetEmailCode(
  payload: AuthEmailCodeRequestPayload,
  signal?: AbortSignal,
): Promise<Response> {
  return fetch(getAuthPasswordResetEmailCodeEndpoint(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  })
}

export async function postAuthPasswordReset(
  payload: AuthPasswordResetRequestPayload,
  signal?: AbortSignal,
): Promise<Response> {
  return fetch(getAuthPasswordResetEndpoint(), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify(payload),
    signal,
  })
}
