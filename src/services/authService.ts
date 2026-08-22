// author: jf

import {
  getAuthLoginKey,
  postAuthEmailCode,
  postAuthLogin,
  postAuthPasswordReset,
  postAuthPasswordResetEmailCode,
  postAuthRegister,
  type AuthEmailCodeResponsePayload,
  type AuthLoginKeyResponsePayload,
  type AuthLoginRequestPayload,
  type AuthLoginResponsePayload,
} from '@/api/authApi'

export type AuthRole = 'admin' | 'user'

export type AiPermission = 'resume_optimize' | 'ai_interview' | 'knowledge_admin'

export interface AuthUser {
  id: string
  username: string
  displayName: string
  role: AuthRole
  permissions: AiPermission[]
}

export interface AuthSession {
  accessToken: string
  user: AuthUser
}

export interface AuthEmailCodeResult {
  cooldownSeconds: number
  expiresInSeconds: number
}

export interface LoginAccountOption {
  username: string
  password: string
  displayName: string
  role: AuthRole
  description: string
}

type DemoAccount = AuthUser & {
  password: string
  description: string
}

const AUTH_STORAGE_KEY = 'resume-builder-auth-session'
const LOGIN_ENCRYPTION_ALGORITHM = 'RSA-OAEP-256+A256GCM'
export const AUTH_SESSION_EXPIRED_EVENT = 'resume-builder:auth-session-expired'

const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    id: 'admin-001',
    username: 'admin',
    password: 'admin123',
    displayName: '知识库管理员',
    role: 'admin',
    permissions: ['resume_optimize', 'ai_interview', 'knowledge_admin'],
    description: '可使用 AI 简历优化、AI 面试和知识库管理。',
  },
  {
    id: 'user-001',
    username: 'user',
    password: 'user123',
    displayName: '求职用户',
    role: 'user',
    permissions: ['resume_optimize', 'ai_interview'],
    description: '可使用 AI 简历优化和 AI 面试，不能维护知识库。',
  },
]

export const AI_PERMISSION_LABELS: Record<AiPermission, string> = {
  resume_optimize: 'AI 简历优化对话',
  ai_interview: 'AI 面试对话',
  knowledge_admin: '知识库上传与维护',
}

export const LOGIN_ACCOUNT_OPTIONS: LoginAccountOption[] = DEMO_ACCOUNTS.map((account) => ({
  username: account.username,
  password: account.password,
  displayName: account.displayName,
  role: account.role,
  description: account.description,
}))

function toAuthUser(account: DemoAccount): AuthUser {
  return {
    id: account.id,
    username: account.username,
    displayName: account.displayName,
    role: account.role,
    permissions: [...account.permissions],
  }
}

function normalizeRole(value: unknown): AuthRole {
  return String(value ?? '').trim() === 'admin' ? 'admin' : 'user'
}

function normalizePermissions(value: unknown): AiPermission[] {
  if (!Array.isArray(value)) return []
  const validPermissions = new Set<AiPermission>(['resume_optimize', 'ai_interview', 'knowledge_admin'])
  return value.filter((permission): permission is AiPermission => validPermissions.has(permission as AiPermission))
}

function normalizeAuthUser(value: unknown): AuthUser | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Partial<AuthUser>
  const id = String(raw.id ?? '').trim()
  const username = String(raw.username ?? '').trim()
  const displayName = String(raw.displayName ?? '').trim()
  const permissions = normalizePermissions(raw.permissions)
  if (id && username && displayName && permissions.length > 0) {
    return {
      id,
      username,
      displayName,
      role: normalizeRole(raw.role),
      permissions,
    }
  }

  const matched = DEMO_ACCOUNTS.find((account) => account.id === raw.id || account.username === raw.username)
  return matched ? toAuthUser(matched) : null
}

function normalizeAuthSession(value: unknown): AuthSession | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Partial<AuthSession>
  const accessToken = String(raw.accessToken ?? '').trim()
  const user = normalizeAuthUser(raw.user)
  if (!accessToken || !user) return null
  return { accessToken, user }
}

function normalizeLoginResponse(payload: AuthLoginResponsePayload): AuthSession | null {
  const user = normalizeAuthUser(payload.user)
  const accessToken = String(payload.accessToken ?? '').trim()
  if (!user || !accessToken) return null
  return { user, accessToken }
}

function readErrorText(value: unknown): string {
  if (typeof value === 'string') return value.trim()
  if (Array.isArray(value)) {
    return value
      .map((item) => {
        if (!item || typeof item !== 'object') return String(item ?? '').trim()
        const raw = item as { msg?: unknown; message?: unknown }
        return readErrorText(raw.message ?? raw.msg)
      })
      .filter(Boolean)
      .join('；')
  }
  return ''
}

const AUTH_FIELD_LABELS: Record<string, string> = {
  username: '登录账号',
  password: '密码',
  email: '邮箱',
  verificationCode: '邮箱验证码',
  newPassword: '新密码',
  displayName: '姓名',
  keyId: '登录密钥标识',
  encryptedKey: '登录加密密钥',
  iv: '登录加密随机数',
  encryptedPassword: '登录密码密文',
  issuedAt: '登录请求时间',
  requestId: '登录请求标识',
}

function localizeAuthErrorMessage(message: string): string {
  let localized = message.trim()
  for (const [fieldName, fieldLabel] of Object.entries(AUTH_FIELD_LABELS)) {
    localized = localized.replace(new RegExp(`\\b${fieldName}\\b`, 'g'), fieldLabel)
  }
  localized = localized.replace(/不能为空不能为空/g, '不能为空')
  return localized
}

async function readAuthErrorMessage(response: Response, fallback: string): Promise<string> {
  const payload = (await response
    .clone()
    .json()
    .catch(() => null)) as { message?: unknown; detail?: unknown } | null
  const payloadMessage = readErrorText(payload?.message) || readErrorText(payload?.detail)
  if (payloadMessage) return localizeAuthErrorMessage(payloadMessage)

  const plainText = await response.text().catch(() => '')
  return plainText.trim() ? localizeAuthErrorMessage(plainText) : fallback
}

function requireWebCrypto(): Crypto {
  const cryptoApi = globalThis.crypto
  if (!cryptoApi?.subtle) {
    throw new Error('当前环境不支持安全登录，请通过 HTTPS 或 localhost 访问后重试。')
  }
  return cryptoApi
}

function decodeBase64(value: string): ArrayBuffer {
  try {
    const binary = globalThis.atob(value.replace(/\s/g, ''))
    const bytes = new Uint8Array(binary.length)
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index)
    }
    return bytes.buffer
  } catch {
    throw new Error('登录加密公钥格式无效，请刷新页面后重试。')
  }
}

function encodeBase64Url(value: BufferSource): string {
  const bytes = value instanceof ArrayBuffer ? new Uint8Array(value) : new Uint8Array(value.buffer, value.byteOffset, value.byteLength)
  let binary = ''
  for (const byte of bytes) binary += String.fromCharCode(byte)
  return globalThis.btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '')
}

function createRequestId(cryptoApi: Crypto): string {
  if (typeof cryptoApi.randomUUID === 'function') return cryptoApi.randomUUID()

  const bytes = cryptoApi.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6]! & 0x0f) | 0x40
  bytes[8] = (bytes[8]! & 0x3f) | 0x80
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

async function requestLoginEncryptionKey(): Promise<AuthLoginKeyResponsePayload> {
  const response = await getAuthLoginKey()
  if (!response.ok) {
    throw new Error(await readAuthErrorMessage(response, '安全登录初始化失败，请稍后重试。'))
  }

  const payload = (await response.json().catch(() => null)) as Partial<AuthLoginKeyResponsePayload> | null
  const keyId = String(payload?.keyId ?? '').trim()
  const publicKey = String(payload?.publicKey ?? '').trim()
  if (payload?.algorithm !== LOGIN_ENCRYPTION_ALGORITHM || !keyId || !publicKey) {
    throw new Error('安全登录初始化响应无效，请稍后重试。')
  }
  return { algorithm: LOGIN_ENCRYPTION_ALGORITHM, keyId, publicKey }
}

async function encryptLoginPassword(username: string, password: string): Promise<AuthLoginRequestPayload> {
  const normalizedUsername = username.trim().toLowerCase()
  const cryptoApi = requireWebCrypto()
  const loginKey = await requestLoginEncryptionKey()
  const issuedAt = Date.now()
  const requestId = createRequestId(cryptoApi)
  const additionalData = new TextEncoder().encode(
    `${normalizedUsername}\n${loginKey.keyId}\n${issuedAt}\n${requestId}`,
  )
  const iv = cryptoApi.getRandomValues(new Uint8Array(12))
  const publicKey = await cryptoApi.subtle.importKey(
    'spki',
    decodeBase64(loginKey.publicKey),
    { name: 'RSA-OAEP', hash: 'SHA-256' },
    false,
    ['encrypt'],
  )
  const aesKey = await cryptoApi.subtle.generateKey({ name: 'AES-GCM', length: 256 }, true, ['encrypt'])
  const rawAesKey = await cryptoApi.subtle.exportKey('raw', aesKey)

  try {
    const passwordBytes = new TextEncoder().encode(password)
    try {
      const [encryptedKey, encryptedPassword] = await Promise.all([
        cryptoApi.subtle.encrypt({ name: 'RSA-OAEP' }, publicKey, rawAesKey),
        cryptoApi.subtle.encrypt({ name: 'AES-GCM', iv, additionalData, tagLength: 128 }, aesKey, passwordBytes),
      ])
      return {
        username: normalizedUsername,
        keyId: loginKey.keyId,
        encryptedKey: encodeBase64Url(encryptedKey),
        iv: encodeBase64Url(iv),
        encryptedPassword: encodeBase64Url(encryptedPassword),
        issuedAt,
        requestId,
      }
    } finally {
      passwordBytes.fill(0)
    }
  } finally {
    new Uint8Array(rawAesKey).fill(0)
  }
}

export async function authenticateUser(username: string, password: string): Promise<AuthSession | null> {
  const encryptedPayload = await encryptLoginPassword(username, password)
  const response = await postAuthLogin(encryptedPayload)
  if (!response.ok) {
    if (response.status !== 401) {
      throw new Error(await readAuthErrorMessage(response, '安全登录服务不可用，请稍后重试。'))
    }
    return null
  }

  const payload = (await response.json().catch(() => null)) as AuthLoginResponsePayload | null
  return payload ? normalizeLoginResponse(payload) : null
}

export async function requestRegistrationEmailCode(email: string): Promise<AuthEmailCodeResult> {
  const response = await postAuthEmailCode({ email: email.trim().toLowerCase() })
  if (!response.ok) {
    throw new Error(await readAuthErrorMessage(response, '验证码发送服务不可用，请稍后重试。'))
  }

  const payload = (await response.json().catch(() => null)) as AuthEmailCodeResponsePayload | null
  const cooldownSeconds = Math.max(0, Math.floor(Number(payload?.cooldownSeconds)))
  const expiresInSeconds = Math.max(0, Math.floor(Number(payload?.expiresInSeconds)))
  if (!Number.isFinite(cooldownSeconds) || cooldownSeconds <= 0 || !Number.isFinite(expiresInSeconds) || expiresInSeconds <= 0) {
    throw new Error('验证码发送响应无效，请稍后重试。')
  }
  return { cooldownSeconds, expiresInSeconds }
}

export async function requestPasswordResetEmailCode(email: string): Promise<AuthEmailCodeResult> {
  const response = await postAuthPasswordResetEmailCode({ email: email.trim().toLowerCase() })
  if (!response.ok) {
    throw new Error(await readAuthErrorMessage(response, '验证码发送服务不可用，请稍后重试。'))
  }

  const payload = (await response.json().catch(() => null)) as AuthEmailCodeResponsePayload | null
  const cooldownSeconds = Math.max(0, Math.floor(Number(payload?.cooldownSeconds)))
  const expiresInSeconds = Math.max(0, Math.floor(Number(payload?.expiresInSeconds)))
  if (
    !Number.isFinite(cooldownSeconds) ||
    cooldownSeconds <= 0 ||
    !Number.isFinite(expiresInSeconds) ||
    expiresInSeconds <= 0
  ) {
    throw new Error('验证码发送响应无效，请稍后重试。')
  }
  return { cooldownSeconds, expiresInSeconds }
}

export async function resetPasswordWithEmailCode(
  email: string,
  verificationCode: string,
  newPassword: string,
): Promise<void> {
  const response = await postAuthPasswordReset({
    email: email.trim().toLowerCase(),
    verificationCode: verificationCode.trim(),
    newPassword,
  })
  if (!response.ok) {
    throw new Error(await readAuthErrorMessage(response, '密码重置服务不可用，请稍后重试。'))
  }
}

export async function registerUser(
  displayName: string,
  email: string,
  verificationCode: string,
  password: string,
): Promise<AuthSession> {
  const response = await postAuthRegister({
    email: email.trim().toLowerCase(),
    verificationCode: verificationCode.trim(),
    password,
    displayName: displayName.trim(),
  })
  if (!response.ok) {
    throw new Error(await readAuthErrorMessage(response, '注册服务不可用，请稍后重试。'))
  }

  const payload = (await response.json().catch(() => null)) as AuthLoginResponsePayload | null
  const session = payload ? normalizeLoginResponse(payload) : null
  if (!session) {
    throw new Error('注册响应缺少登录信息，请稍后重试。')
  }
  return session
}

export function loadStoredAuthSession(): AuthSession | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY)
    if (!raw) return null
    return normalizeAuthSession(JSON.parse(raw))
  } catch {
    return null
  }
}

export function saveStoredAuthSession(session: AuthSession): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session))
  } catch {
    // 本地存储不可用时仍允许当前页面会话继续使用。
  }
}

export function clearStoredAuthSession(): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.removeItem(AUTH_STORAGE_KEY)
  } catch {
    // 清理失败不影响当前内存态退出。
  }
}

function notifyAuthSessionExpired(): void {
  clearStoredAuthSession()
  if (typeof window === 'undefined') return
  window.dispatchEvent(new Event(AUTH_SESSION_EXPIRED_EVENT))
}

export function getPermissionLabels(user: AuthUser | null): string[] {
  if (!user) return []
  return user.permissions.map((permission) => AI_PERMISSION_LABELS[permission]).filter(Boolean)
}

export function hasPermission(user: AuthUser | null, permission: AiPermission): boolean {
  return Boolean(user?.permissions.includes(permission))
}

export function buildAuthHeaders(): Record<string, string> {
  const session = loadStoredAuthSession()
  if (!session) return {}

  return {
    Authorization: `Bearer ${session.accessToken}`,
  }
}

export async function fetchWithAuth(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  Object.entries(buildAuthHeaders()).forEach(([name, value]) => headers.set(name, value))

  const response = await fetch(input, { ...init, headers })
  if (response.status === 401) notifyAuthSessionExpired()
  return response
}
