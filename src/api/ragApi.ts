// author: jf
import { API_BASE_PATH } from './apiBase'
import { fetchWithAuth } from '@/services/authService'

const RAG_UPLOAD_TIMEOUT_MS = 300_000

export interface RagUploadFileResult {
  fileName: string
  contentType: string
  sourceType: string
  ingestSource: string
  chunkCount: number
  insertedCount: number
  status: string
  errorMessage?: string | null
}

export interface RagUploadResponse {
  totalFiles: number
  succeededFiles: number
  failedFiles: number
  inserted: number
  files: RagUploadFileResult[]
}

export interface RagUploadProgressEvent {
  event: string
  traceId?: string
  trace_id?: string
  fileIndex?: number
  file_index?: number
  totalFiles?: number
  total_files?: number
  fileName?: string
  file_name?: string
  stage?: string
  status?: string
  message?: string
  result?: unknown
  summary?: unknown
  files?: unknown
  succeededFiles?: number
  succeeded_files?: number
  failedFiles?: number
  failed_files?: number
  inserted?: number
  progressPercent?: number
  progress_percent?: number
  fileProgressPercent?: number
  file_progress_percent?: number
}

export interface RagUploadStreamCallbacks {
  onEvent: (event: RagUploadProgressEvent) => void
}

export function getRagUploadEndpoint(): string {
  return `${API_BASE_PATH}/ai/rag/upload`
}

export function getRagUploadStreamEndpoint(): string {
  return `${API_BASE_PATH}/ai/rag/upload/stream`
}

export async function uploadKnowledgeAssets(
  files: File[],
  signal?: AbortSignal
): Promise<RagUploadResponse> {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }

  const requestController = new AbortController()
  let didTimeout = false
  const handleExternalAbort = () => requestController.abort(signal?.reason)
  if (signal) {
    if (signal.aborted) {
      requestController.abort(signal.reason)
    } else {
      signal.addEventListener('abort', handleExternalAbort, { once: true })
    }
  }
  const timeoutId = setTimeout(() => {
    didTimeout = true
    requestController.abort()
  }, RAG_UPLOAD_TIMEOUT_MS)

  let response: Response
  try {
    response = await fetchWithAuth(getRagUploadEndpoint(), {
      method: 'POST',
      headers: {
        Accept: 'application/json',
      },
      body: formData,
      signal: requestController.signal,
    })
  } catch (error) {
    if (didTimeout) {
      throw new Error(
        `知识库上传超时（${Math.floor(RAG_UPLOAD_TIMEOUT_MS / 1000)} 秒），请检查 Embedding 服务与 pgvector 连接`
      )
    }
    if (signal?.aborted) {
      throw new Error('已取消上传')
    }
    if (error instanceof Error && error.message) {
      throw new Error(`知识库上传失败：${error.message}`)
    }
    throw new Error('知识库上传失败')
  } finally {
    clearTimeout(timeoutId)
    if (signal) {
      signal.removeEventListener('abort', handleExternalAbort)
    }
  }

  const payload = (await response.json().catch(() => null)) as
    | RagUploadResponse
    | { detail?: string }
    | null

  if (!response.ok) {
    throw new Error(payload && 'detail' in payload && payload.detail ? payload.detail : '知识库上传失败')
  }

  if (!payload || !('files' in payload)) {
    throw new Error('知识库上传返回了无效响应')
  }

  return payload
}

export async function uploadKnowledgeAssetsStream(
  files: File[],
  callbacks: RagUploadStreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }

  const response = await fetchWithAuth(getRagUploadStreamEndpoint(), {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
    },
    body: formData,
    signal,
  })

  if (!response.ok) {
    const errorText = await response.text().catch(() => '')
    throw new Error(errorText.trim() || `知识库上传失败 (${response.status})`)
  }

  const reader = response.body?.getReader()
  if (!reader) {
    throw new Error('知识库上传未返回可读取的进度流')
  }

  const decoder = new TextDecoder()
  let buffer = ''
  let eventName = 'message'
  let dataLines: string[] = []

  const dispatchEvent = () => {
    if (dataLines.length === 0) {
      eventName = 'message'
      return
    }

    const data = dataLines.join('\n')
    dataLines = []
    const parsed = parseProgressEventData(data)
    const event = { ...parsed, event: parsed.event || eventName }

    callbacks.onEvent(event)
    if (event.event === 'error') {
      throw new Error(event.message || '知识库上传失败')
    }

    eventName = 'message'
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const rawLine of lines) {
      const line = rawLine.replace(/\r$/, '')
      if (!line) {
        dispatchEvent()
        continue
      }
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim() || 'message'
        continue
      }
      if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart())
      }
    }
  }

  buffer += decoder.decode()
  if (buffer.trim()) {
    for (const rawLine of buffer.split('\n')) {
      const line = rawLine.replace(/\r$/, '')
      if (!line) {
        dispatchEvent()
        continue
      }
      if (line.startsWith('event:')) {
        eventName = line.slice(6).trim() || 'message'
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart())
      }
    }
  }
  if (dataLines.length > 0) {
    dispatchEvent()
  }
}

function parseProgressEventData(data: string): RagUploadProgressEvent {
  try {
    const parsed = JSON.parse(data) as RagUploadProgressEvent
    return parsed && typeof parsed === 'object' ? parsed : { event: 'message', message: data }
  } catch {
    return { event: 'message', message: data }
  }
}
