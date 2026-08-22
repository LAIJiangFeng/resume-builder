// author: jf
import {
  getInterviewSessionDetail as fetchInterviewSessionDetailResponse,
  getInterviewSessions as fetchInterviewSessionsResponse,
  postInterviewTurnStream,
} from '@/api/interviewApi'
import type {
  FinalEvaluation,
  InterviewSessionDetail,
  InterviewSessionMessage,
  InterviewSessionSummary,
  InterviewStreamEvent,
  InterviewTurnRequestCompat,
  InterviewPhase,
  InterviewTurnResponse,
  InterviewTurnScore,
  InterviewTurnStreamCallbacks,
} from '@/services/interview/types'

export type {
  FinalEvaluation,
  InterviewCommand,
  InterviewHistoryItem,
  InterviewMode,
  InterviewPhase,
  InterviewRequestState,
  InterviewSessionDetail,
  InterviewSessionMessage,
  InterviewSessionSummary,
  InterviewTurnRequest,
  InterviewTurnRequestCompat,
  InterviewTurnScore,
  InterviewTurnStreamCallbacks,
  LegacyInterviewConfig,
  ResumeSnapshot,
} from '@/services/interview/types'

function clampScore(value: unknown): number {
  if (typeof value !== 'number' || Number.isNaN(value)) return 0
  return Math.max(0, Math.min(100, Math.round(value)))
}

function parseDateTimeText(value: unknown): string {
  return String(value ?? '').trim()
}

function normalizeContentValue(value: unknown): string {
  if (typeof value === 'string') return value.trim()
  if (typeof value === 'number' || typeof value === 'boolean') return String(value).trim()
  if (Array.isArray(value)) {
    return value
      .map((item) => normalizeContentValue(item))
      .filter(Boolean)
      .join('\n')
      .trim()
  }
  if (!value || typeof value !== 'object') return ''

  const source = value as Record<string, unknown>
  for (const key of ['assistantReply', 'content', 'text', 'message', 'value', 'outputText', 'output_text']) {
    const content = normalizeContentValue(source[key])
    if (content) return content
  }

  return ''
}

function extractAssistantReplyJson(text: string): string {
  const cleaned = text.trim()
  if (!cleaned) return ''

  try {
    const jsonText = (() => {
      if (cleaned.startsWith('{') && cleaned.endsWith('}')) return cleaned
      const first = cleaned.indexOf('{')
      const last = cleaned.lastIndexOf('}')
      if (first >= 0 && last > first) return cleaned.slice(first, last + 1)
      return ''
    })()
    if (!jsonText) return ''

    const parsed = JSON.parse(jsonText) as { assistantReply?: unknown }
    return normalizeContentValue(parsed.assistantReply)
  } catch {
    return ''
  }
}

function extractSessionMessageContent(source: Record<string, unknown>, role: 'assistant' | 'user'): string {
  for (const key of ['content', 'messageContent', 'message_content', 'message', 'text', 'assistantReply', 'assistant_reply', 'reply', 'answer']) {
    const content = normalizeContentValue(source[key])
    if (!content) continue

    if (role === 'assistant') {
      return extractAssistantReplyJson(content) || content
    }

    return content
  }

  return ''
}

function normalizeTurnScore(value: unknown): InterviewTurnScore | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  return {
    score: clampScore(raw.score),
    comment: String(raw.comment ?? '').trim(),
  }
}

function normalizeFinalEvaluation(value: unknown): FinalEvaluation | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>

  return {
    projectScore: clampScore(raw.projectScore),
    skillScore: clampScore(raw.skillScore),
    workScore: clampScore(raw.workScore),
    educationScore: clampScore(raw.educationScore),
    totalScore: clampScore(raw.totalScore),
    passed: Boolean(raw.passed),
    summary: String(raw.summary ?? '').trim(),
    improvements: Array.isArray(raw.improvements) ? raw.improvements.map((item) => String(item).trim()).filter(Boolean) : [],
  }
}

function normalizeSessionStatus(value: unknown): 'active' | 'finished' {
  return String(value ?? '').trim().toLowerCase() === 'finished' ? 'finished' : 'active'
}

function normalizeSessionMode(value: unknown): 'candidate' | 'interviewer' {
  return String(value ?? '').trim().toLowerCase() === 'interviewer' ? 'interviewer' : 'candidate'
}

function extractErrorText(text: string): string {
  const cleaned = text.trim()
  if (!cleaned) return ''
  try {
    const parsed = JSON.parse(cleaned) as { error?: string; message?: string }
    return parsed.message?.trim() || parsed.error?.trim() || cleaned
  } catch {
    return cleaned
  }
}

function parseNdjsonLine(line: string): InterviewStreamEvent | null {
  const trimmed = line.trim()
  if (!trimmed) return null

  try {
    const parsed = JSON.parse(trimmed) as Record<string, unknown>
    const event = typeof parsed.event === 'string' && parsed.event.trim() ? parsed.event.trim() : 'message'
    const data = typeof parsed.data === 'string' ? parsed.data : String(parsed.data ?? '')
    return { event, data }
  } catch {
    return null
  }
}

function assertNdjsonResponse(response: Response) {
  const contentType = (response.headers.get('content-type') || '').toLowerCase()
  const isNdjson =
    contentType.includes('application/x-ndjson') ||
    contentType.includes('application/stream+json') ||
    contentType.includes('ndjson')

  if (!isNdjson || !response.body) {
    throw new Error('Interview stream requires NDJSON response body')
  }
}

async function parseJsonResponse(response: Response): Promise<unknown> {
  const text = await response.text().catch(() => '')
  if (!text.trim()) return null

  try {
    return JSON.parse(text)
  } catch {
    throw new Error(`Unexpected non-JSON response: ${text.slice(0, 200)}`)
  }
}

async function requestInterviewTurnPayload(
  requestBody: Omit<InterviewTurnRequestCompat, 'config'>,
  signal?: AbortSignal,
  callbacks?: InterviewTurnStreamCallbacks
): Promise<unknown> {
  const response = await postInterviewTurnStream(requestBody, signal)

  if (!response.ok) {
    const errorText = extractErrorText(await response.text().catch(() => ''))
    throw new Error(`Interview request failed (${response.status}): ${errorText || response.statusText}`)
  }

  assertNdjsonResponse(response)

  const reader = response.body!.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let latestAssistantReply = ''
  let finalPayload: unknown = null

  const handleLine = (line: string) => {
    const parsed = parseNdjsonLine(line)
    if (!parsed) return

    if (parsed.event === 'accepted') {
      callbacks?.onAccepted?.(parsed.data)
      return
    }

    if (parsed.event === 'processing') {
      callbacks?.onProcessing?.(parsed.data)
      return
    }

    if (parsed.event === 'chunk') {
      latestAssistantReply = parsed.data
      callbacks?.onAssistantReplyChunk?.(latestAssistantReply)
      return
    }

    if (parsed.event === 'done') {
      try {
        finalPayload = JSON.parse(parsed.data)
      } catch {
        finalPayload = { assistantReply: latestAssistantReply || parsed.data }
      }
      return
    }

    if (parsed.event === 'error') {
      throw new Error(parsed.data || 'Interview stream failed')
    }
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    buffer = buffer.replace(/\r\n/g, '\n')

    let lineBreakIndex = buffer.indexOf('\n')
    while (lineBreakIndex >= 0) {
      const line = buffer.slice(0, lineBreakIndex)
      buffer = buffer.slice(lineBreakIndex + 1)
      handleLine(line)
      lineBreakIndex = buffer.indexOf('\n')
    }
  }

  buffer += decoder.decode()
  buffer = buffer.replace(/\r\n/g, '\n')
  if (buffer.trim()) {
    handleLine(buffer)
  }

  if (finalPayload != null) {
    return finalPayload
  }
  if (latestAssistantReply) {
    return { assistantReply: latestAssistantReply }
  }
  throw new Error('Interview stream ended without done event')
}

function normalizeTurnResponse(input: unknown): InterviewTurnResponse {
  const source = (input || {}) as Record<string, unknown>

  return {
    assistantReply: String(source.assistantReply ?? '').trim() || 'Empty response from backend.',
    phase: (String(source.phase ?? 'opening') as InterviewPhase) || 'opening',
    nextAction: String(source.nextAction ?? '') === 'finish' ? 'finish' : 'continue',
    turnScore: normalizeTurnScore(source.turnScore),
    finalEvaluation: normalizeFinalEvaluation(source.finalEvaluation),
    memorySummary: String(source.memorySummary ?? '').trim(),
    sessionId: String(source.sessionId ?? '').trim(),
  }
}

function normalizeSessionSummary(input: unknown): InterviewSessionSummary {
  const source = (input || {}) as Record<string, unknown>

  return {
    sessionId: String(source.sessionId ?? '').trim(),
    mode: normalizeSessionMode(source.mode),
    status: normalizeSessionStatus(source.status),
    durationMinutes: Math.max(1, Number(source.durationMinutes ?? 0) || 60),
    elapsedSeconds: Math.max(0, Number(source.elapsedSeconds ?? 0) || 0),
    messageCount: Math.max(0, Number(source.messageCount ?? 0) || 0),
    totalScore: source.totalScore == null ? null : clampScore(source.totalScore),
    passed: source.passed == null ? null : Boolean(source.passed),
    lastMessagePreview: String(source.lastMessagePreview ?? '').trim(),
    createdAt: parseDateTimeText(source.createdAt),
    updatedAt: parseDateTimeText(source.updatedAt),
  }
}

function normalizeSessionMessage(input: unknown): InterviewSessionMessage | null {
  if (!input || typeof input !== 'object') return null
  const source = input as Record<string, unknown>

  const role = String(source.role ?? '').trim().toLowerCase() === 'assistant' ? 'assistant' : 'user'
  const content = extractSessionMessageContent(source, role)
  if (!content) return null

  return {
    role,
    content,
    score: normalizeTurnScore(source.score),
  }
}

function normalizeSessionDetail(input: unknown): InterviewSessionDetail {
  const source = (input || {}) as Record<string, unknown>
  const messages = Array.isArray(source.messages)
    ? source.messages.map((item) => normalizeSessionMessage(item)).filter((item): item is InterviewSessionMessage => item !== null)
    : []

  return {
    sessionId: String(source.sessionId ?? '').trim(),
    mode: normalizeSessionMode(source.mode),
    status: normalizeSessionStatus(source.status),
    durationMinutes: Math.max(1, Number(source.durationMinutes ?? 0) || 60),
    elapsedSeconds: Math.max(0, Number(source.elapsedSeconds ?? 0) || 0),
    memorySummary: String(source.memorySummary ?? '').trim(),
    finalEvaluation: normalizeFinalEvaluation(source.finalEvaluation),
    resumeSnapshot: (source.resumeSnapshot ?? null) as InterviewSessionDetail['resumeSnapshot'],
    messages,
    createdAt: parseDateTimeText(source.createdAt),
    updatedAt: parseDateTimeText(source.updatedAt),
  }
}

export async function requestInterviewTurn(
  request: InterviewTurnRequestCompat,
  signal?: AbortSignal,
  callbacks?: InterviewTurnStreamCallbacks
): Promise<InterviewTurnResponse> {
  const { config: _legacyConfig, ...requestBody } = request
  const payload = await requestInterviewTurnPayload(requestBody, signal, callbacks)
  const normalized = normalizeTurnResponse(payload)

  if (normalized.assistantReply) {
    callbacks?.onAssistantReplyChunk?.(normalized.assistantReply)
  }
  return normalized
}

export async function listInterviewSessions(limit = 20, signal?: AbortSignal): Promise<InterviewSessionSummary[]> {
  const response = await fetchInterviewSessionsResponse(limit, signal)
  if (!response.ok) {
    const errorText = extractErrorText(await response.text().catch(() => ''))
    throw new Error(`Fetch interview sessions failed (${response.status}): ${errorText || response.statusText}`)
  }

  const payload = await parseJsonResponse(response)
  if (!Array.isArray(payload)) return []

  return payload
    .map((item) => normalizeSessionSummary(item))
    .filter((item) => item.sessionId)
}

export async function getInterviewSessionDetail(sessionId: string, signal?: AbortSignal): Promise<InterviewSessionDetail> {
  const safeSessionId = String(sessionId || '').trim()
  if (!safeSessionId) {
    throw new Error('sessionId cannot be empty')
  }

  const response = await fetchInterviewSessionDetailResponse(safeSessionId, signal)
  if (!response.ok) {
    const errorText = extractErrorText(await response.text().catch(() => ''))
    throw new Error(`Fetch interview session detail failed (${response.status}): ${errorText || response.statusText}`)
  }

  const payload = await parseJsonResponse(response)
  return normalizeSessionDetail(payload)
}
