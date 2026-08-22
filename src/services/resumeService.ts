// author: jf
import {
  deleteResume as deleteResumeRequest,
  getResume as getResumeRequest,
  getResumes as getResumesRequest,
  postActivateResume,
  postDuplicateResume,
  postResume,
  putResume,
} from '@/api/resumeApi'

export interface ResumeSummary {
  resumeId: string
  name: string
  active: boolean
  createdAt: string
  updatedAt: string
}

export interface StoredResume extends ResumeSummary {
  data: Record<string, unknown>
}

async function parseError(response: Response, fallback: string): Promise<Error> {
  const payload = (await response.clone().json().catch(() => null)) as
    | { message?: unknown; detail?: unknown; error?: unknown }
    | null
  const message = String(payload?.message ?? payload?.detail ?? payload?.error ?? '').trim()
  const plainText = await response.text().catch(() => '')
  return new Error(message || plainText.trim() || fallback)
}

function normalizeSummary(value: unknown): ResumeSummary {
  const source = (value ?? {}) as Record<string, unknown>
  return {
    resumeId: String(source.resumeId ?? '').trim(),
    name: String(source.name ?? '').trim() || '未命名简历',
    active: Boolean(source.active),
    createdAt: String(source.createdAt ?? '').trim(),
    updatedAt: String(source.updatedAt ?? '').trim(),
  }
}

function normalizeResume(value: unknown): StoredResume {
  const source = (value ?? {}) as Record<string, unknown>
  const data = source.data && typeof source.data === 'object' && !Array.isArray(source.data)
    ? source.data as Record<string, unknown>
    : {}
  return { ...normalizeSummary(source), data }
}

async function parseResumeResponse(response: Response, fallback: string): Promise<StoredResume> {
  if (!response.ok) throw await parseError(response, fallback)
  return normalizeResume(await response.json())
}

export async function listStoredResumes(signal?: AbortSignal): Promise<ResumeSummary[]> {
  const response = await getResumesRequest(signal)
  if (!response.ok) throw await parseError(response, '简历列表加载失败')
  const payload = await response.json().catch(() => [])
  return Array.isArray(payload)
    ? payload.map(normalizeSummary).filter((item) => item.resumeId)
    : []
}

export async function loadStoredResume(resumeId: string, signal?: AbortSignal): Promise<StoredResume> {
  return parseResumeResponse(await getResumeRequest(resumeId, signal), '简历加载失败')
}

export async function createStoredResume(
  name: string,
  data: Record<string, unknown>,
): Promise<StoredResume> {
  return parseResumeResponse(await postResume({ name, data }), '简历创建失败')
}

export async function updateStoredResume(
  resumeId: string,
  name: string,
  data: Record<string, unknown>,
): Promise<StoredResume> {
  return parseResumeResponse(await putResume(resumeId, { name, data }), '简历保存失败')
}

export async function activateStoredResume(resumeId: string): Promise<StoredResume> {
  return parseResumeResponse(await postActivateResume(resumeId), '简历切换失败')
}

export async function duplicateStoredResume(resumeId: string): Promise<StoredResume> {
  return parseResumeResponse(await postDuplicateResume(resumeId), '简历复制失败')
}

export async function removeStoredResume(resumeId: string): Promise<void> {
  const response = await deleteResumeRequest(resumeId)
  if (!response.ok) throw await parseError(response, '简历删除失败')
}
