<!-- author: jf -->
<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import {
  Blocks,
  CircleX,
  CloudUpload,
  DatabaseZap,
  FileText,
  FileUp,
  Image as ImageIcon,
  ListChecks,
  Play,
  ScanText,
  Server,
  ShieldCheck,
  Trash2,
} from 'lucide-vue-next'
import {
  uploadKnowledgeAssetsStream,
  type RagUploadFileResult,
  type RagUploadProgressEvent,
  type RagUploadResponse,
} from '@/api/ragApi'

type LocalUploadStatus = 'pending' | 'queued' | 'uploading' | 'success' | 'failed' | 'cancelled'

type LocalUploadItem = Omit<RagUploadFileResult, 'status'> & {
  status: LocalUploadStatus
  fileSize: number
  order: number
  stage?: string
  stageProgress: number
}

type UploadPhase = 'idle' | 'ready' | 'uploading' | 'completed' | 'error'

type CompactMetric = {
  icon: 'files' | 'checks' | 'chunks'
  label: string
  value: string
}

type GuidanceFact = {
  icon: 'format' | 'limit' | 'target' | 'type'
  label: string
  value: string
}

const ACCEPT = '.pdf,.txt,.md,.docx,.png,.jpg,.jpeg,.webp'
const UPLOAD_STAGE_PROGRESS: Array<{ keyword: string; progress: number }> = [
  { keyword: '排队', progress: 0 },
  { keyword: '开始', progress: 0.08 },
  { keyword: '读取', progress: 0.16 },
  { keyword: '校验', progress: 0.25 },
  { keyword: '解析', progress: 0.38 },
  { keyword: '规范化', progress: 0.5 },
  { keyword: '逻辑文档拆分', progress: 0.6 },
  { keyword: '拆分', progress: 0.6 },
  { keyword: '切块', progress: 0.72 },
  { keyword: 'Embedding', progress: 0.84 },
  { keyword: '入库', progress: 0.94 },
  { keyword: '完成', progress: 1 },
]
const selectedFiles = ref<File[]>([])
const uploadItems = ref<LocalUploadItem[]>([])
const uploadSummary = ref<RagUploadResponse | null>(null)
const errorMessage = ref('')
const isUploading = ref(false)
const isDragOver = ref(false)
const displayedUploadProgressPercent = ref(0)
const backendUploadProgressPercent = ref<number | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)
let abortController: AbortController | null = null
let progressAnimationTimer: number | null = null

const hasFiles = computed(() => selectedFiles.value.length > 0)
const hasUploadItems = computed(() => uploadItems.value.length > 0)
const totalFiles = computed(() => uploadSummary.value?.totalFiles ?? selectedFiles.value.length)
const succeededFiles = computed(() => uploadSummary.value?.succeededFiles ?? countUploadItems(['success']))
const failedFiles = computed(() => uploadSummary.value?.failedFiles ?? countUploadItems(['failed']))
const cancelledFiles = computed(() => countUploadItems(['cancelled']))
const insertedChunks = computed(
  () => uploadSummary.value?.inserted ?? uploadItems.value.reduce((sum, item) => sum + item.insertedCount, 0)
)
const totalSelectedSize = computed(() => selectedFiles.value.reduce((sum, file) => sum + file.size, 0))
const totalSelectedSizeLabel = computed(() => formatFileSize(totalSelectedSize.value))
const processedFiles = computed(() => countUploadItems(['success', 'failed']))
const activeUploadIndex = computed(() => uploadItems.value.findIndex((item) => item.status === 'uploading'))
const activeUploadItem = computed(() => {
  if (activeUploadIndex.value < 0) return null
  return uploadItems.value[activeUploadIndex.value] ?? null
})
const uploadProgressPercent = computed(() => {
  const total = totalFiles.value
  if (total <= 0) return 0
  if (uploadPhase.value === 'completed' && cancelledFiles.value === 0) return 100
  if (uploadPhase.value === 'ready' || uploadPhase.value === 'idle') return 0
  if (backendUploadProgressPercent.value !== null) {
    const percent = backendUploadProgressPercent.value
    if (isUploading.value) return Math.min(99, Math.max(4, percent))
    return percent
  }
  const weightedProgress = uploadItems.value.reduce((sum, item) => sum + resolveItemProgress(item), 0)
  const percent = Math.round((weightedProgress / total) * 100)
  if (isUploading.value) return Math.min(99, Math.max(4, percent))
  return percent
})
const uploadProgressText = computed(() => {
  if (isUploading.value && activeUploadItem.value) {
    const stageText = activeUploadItem.value.stage ? `（${activeUploadItem.value.stage}）` : ''
    return `正在处理第 ${activeUploadItem.value.order}/${totalFiles.value} 个：${activeUploadItem.value.fileName}${stageText}`
  }
  if (isUploading.value) {
    return `正在处理文件，请稍等，已完成 ${processedFiles.value}/${totalFiles.value} 个`
  }
  if (uploadPhase.value === 'completed') {
    return failedFiles.value > 0
      ? `已处理 ${processedFiles.value}/${totalFiles.value} 个文件，${failedFiles.value} 个失败`
      : `已完成 ${totalFiles.value} 个文件`
  }
  if (uploadPhase.value === 'error') {
    if (cancelledFiles.value > 0) return `已取消，已处理 ${processedFiles.value}/${totalFiles.value} 个文件`
    return `上传中断，已处理 ${processedFiles.value}/${totalFiles.value} 个文件`
  }
  if (uploadPhase.value === 'ready') return `等待开始，共 ${totalFiles.value} 个文件`
  return '等待选择文件'
})
const progressAssistText = computed(() => {
  const cancelledText = cancelledFiles.value > 0 ? `，取消 ${cancelledFiles.value}` : ''
  return `成功 ${succeededFiles.value}，失败 ${failedFiles.value}${cancelledText}，Chunk ${insertedChunks.value}`
})

const uploadPhase = computed<UploadPhase>(() => {
  if (isUploading.value) return 'uploading'
  if (errorMessage.value) return 'error'
  if (uploadSummary.value) return 'completed'
  if (selectedFiles.value.length > 0) return 'ready'
  return 'idle'
})

watch(uploadProgressPercent, (targetPercent) => {
  animateDisplayedProgress(targetPercent)
})

onUnmounted(() => {
  stopProgressAnimation()
})

const compactSummary = computed(() => {
  switch (uploadPhase.value) {
    case 'ready':
      return `已选 ${totalFiles.value} 个文件，共 ${totalSelectedSizeLabel.value}`
    case 'uploading':
      return uploadProgressText.value
    case 'completed':
      return `本批次已完成，成功 ${succeededFiles.value}，失败 ${failedFiles.value}`
    case 'error':
      return errorMessage.value || '上传未完成，请查看当前批次状态'
    default:
      return '文档与图片可混合上传，结果会在下方直接更新'
  }
})

const compactMetrics = computed<CompactMetric[]>(() => [
  { icon: 'files', label: '文件', value: String(totalFiles.value) },
  { icon: 'checks', label: '成功/失败', value: `${succeededFiles.value}/${failedFiles.value}` },
  { icon: 'chunks', label: 'Chunk', value: String(insertedChunks.value) },
])

const resultSectionTitle = computed(() => {
  switch (uploadPhase.value) {
    case 'completed':
      return '处理结果'
    case 'uploading':
      return '当前进度'
    case 'error':
      return '错误与进度'
    default:
      return '当前批次'
  }
})

const emptyStateTitle = computed(() => {
  if (uploadPhase.value === 'error') return '本次上传未完成'
  return '从这里开始整理知识库资料'
})

const emptyStateText = computed(() => {
  if (uploadPhase.value === 'error') {
    return errorMessage.value || '请重新选择文件并再次发起上传。'
  }
  return '选择文件后，会在这里直接看到当前批次和处理结果。'
})

const guidanceFacts: GuidanceFact[] = [
  { icon: 'format', label: '支持格式', value: 'PDF / TXT / MD / DOCX / PNG / JPG / JPEG / WEBP' },
  { icon: 'limit', label: '单文件限制', value: '10 MB' },
  { icon: 'target', label: '写入目标', value: 'pgvector' },
  { icon: 'type', label: '支持类型', value: '文档 / 图片' },
]

function openFilePicker() {
  if (isUploading.value) return
  fileInputRef.value?.click()
}

function onFileChange(event: Event) {
  if (isUploading.value) return
  const input = event.target as HTMLInputElement
  syncSelectedFiles(input.files ? Array.from(input.files) : [])
  input.value = ''
}

function onDrop(event: DragEvent) {
  event.preventDefault()
  isDragOver.value = false
  if (isUploading.value) return
  syncSelectedFiles(event.dataTransfer?.files ? Array.from(event.dataTransfer.files) : [])
}

function syncSelectedFiles(files: File[]) {
  if (files.length === 0) return
  const baseFiles = uploadPhase.value === 'ready' ? selectedFiles.value : []
  selectedFiles.value = dedupeFiles([...baseFiles, ...files])
  resetUploadFeedback()
  syncPendingUploadItems()
}

function removeFile(index: number) {
  if (isUploading.value) return
  selectedFiles.value = selectedFiles.value.filter((_, itemIndex) => itemIndex !== index)
  resetUploadFeedback()
  syncPendingUploadItems()
}

function clearFiles() {
  if (isUploading.value) return
  selectedFiles.value = []
  uploadItems.value = []
  resetUploadFeedback()
}

async function handleUpload() {
  if (!hasFiles.value || isUploading.value) return

  const filesToUpload = [...selectedFiles.value]
  isUploading.value = true
  resetUploadFeedback()
  abortController = new AbortController()
  const signal = abortController.signal
  uploadItems.value = filesToUpload.map((file, index) => createPendingItem(file, 'queued', index + 1))

  try {
    await uploadKnowledgeAssetsStream(
      filesToUpload,
      {
        onEvent: (event) => handleUploadProgressEvent(event, filesToUpload),
      },
      signal
    )
    if (!uploadSummary.value) {
      uploadSummary.value = buildUploadSummary(uploadItems.value)
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : '知识库上传失败'
    if (signal.aborted || (error instanceof DOMException && error.name === 'AbortError')) {
      errorMessage.value = '已取消上传，已保留当前批次进度。'
      const startIndex = activeUploadIndex.value >= 0 ? activeUploadIndex.value : processedFiles.value
      markCancelledItems(startIndex)
    } else {
      errorMessage.value = message
      markInterruptedItems(message)
    }
  }

  isUploading.value = false
  if (!uploadSummary.value) {
    uploadSummary.value = buildUploadSummary(uploadItems.value)
  }
  abortController = null
}

function cancelUpload() {
  abortController?.abort()
}

function resetUploadFeedback() {
  uploadSummary.value = null
  errorMessage.value = ''
  backendUploadProgressPercent.value = null
  animateDisplayedProgress(0)
}

function syncPendingUploadItems() {
  uploadItems.value = selectedFiles.value.map((file, index) => createPendingItem(file, 'pending', index + 1))
}

function createPendingItem(file: File, status: LocalUploadStatus, order: number): LocalUploadItem {
  const sourceType = guessSourceType(file.name)
  return {
    fileName: file.name,
    contentType: file.type || 'application/octet-stream',
    sourceType,
    ingestSource: sourceType === 'image' ? 'image_ocr_text' : 'text_document',
    chunkCount: 0,
    insertedCount: 0,
    status,
    errorMessage: null,
    fileSize: file.size,
    order,
    stage: status === 'queued' ? '排队' : undefined,
    stageProgress: status === 'queued' ? 0 : resolveStageProgress(),
  }
}

function createResultItem(
  result: RagUploadFileResult,
  file: File,
  order: number,
  stage?: string,
  stageProgress?: number
): LocalUploadItem {
  return {
    ...result,
    status: normalizeUploadStatus(result.status),
    fileSize: file.size,
    order,
    stage,
    stageProgress: stageProgress ?? resolveResultProgress(result.status, stage),
  }
}

function createFailedItem(file: File, order: number, message: string): LocalUploadItem {
  return {
    ...createPendingItem(file, 'failed', order),
    errorMessage: message,
  }
}

function replaceUploadItem(index: number, item: LocalUploadItem) {
  uploadItems.value = uploadItems.value.map((currentItem, currentIndex) =>
    currentIndex === index ? item : currentItem
  )
}

function patchUploadItem(index: number, patch: Partial<LocalUploadItem>) {
  uploadItems.value = uploadItems.value.map((currentItem, currentIndex) =>
    currentIndex === index ? { ...currentItem, ...patch } : currentItem
  )
}

function markCancelledItems(startIndex: number) {
  uploadItems.value = uploadItems.value.map((item, index) => {
    if (index < startIndex || item.status === 'success' || item.status === 'failed') return item
    return {
      ...item,
      status: 'cancelled',
      errorMessage: '已取消上传',
      stageProgress: item.stageProgress,
    }
  })
}

function markInterruptedItems(message: string) {
  uploadItems.value = uploadItems.value.map((item) => {
    if (item.status === 'success' || item.status === 'failed' || item.status === 'cancelled') return item
    if (item.status === 'uploading') {
      return {
        ...item,
        status: 'failed',
        errorMessage: message,
        stageProgress: Math.max(item.stageProgress, 1),
      }
    }
    return {
      ...item,
      status: 'cancelled',
      errorMessage: '请求中断，未进入处理',
      stageProgress: item.stageProgress,
    }
  })
}

function buildUploadSummary(items: LocalUploadItem[]): RagUploadResponse {
  return {
    totalFiles: items.length,
    succeededFiles: items.filter((item) => item.status === 'success').length,
    failedFiles: items.filter((item) => item.status === 'failed').length,
    inserted: items.reduce((sum, item) => sum + item.insertedCount, 0),
    files: items.map(toRagUploadFileResult),
  }
}

function toRagUploadFileResult(item: LocalUploadItem): RagUploadFileResult {
  return {
    fileName: item.fileName,
    contentType: item.contentType,
    sourceType: item.sourceType,
    ingestSource: item.ingestSource,
    chunkCount: item.chunkCount,
    insertedCount: item.insertedCount,
    status: item.status,
    errorMessage: item.errorMessage,
  }
}

function countUploadItems(statuses: LocalUploadStatus[]): number {
  const statusSet = new Set<LocalUploadStatus>(statuses)
  return uploadItems.value.filter((item) => statusSet.has(item.status)).length
}

function animateDisplayedProgress(targetPercent: number) {
  const normalizedTarget = clampProgress(targetPercent)
  if (normalizedTarget <= displayedUploadProgressPercent.value) {
    displayedUploadProgressPercent.value = normalizedTarget
    stopProgressAnimation()
    return
  }

  stopProgressAnimation()
  progressAnimationTimer = window.setInterval(() => {
    const distance = normalizedTarget - displayedUploadProgressPercent.value
    if (distance <= 0) {
      displayedUploadProgressPercent.value = normalizedTarget
      stopProgressAnimation()
      return
    }

    const step = Math.max(1, Math.ceil(distance / 5))
    displayedUploadProgressPercent.value = Math.min(normalizedTarget, displayedUploadProgressPercent.value + step)
  }, 80)
}

function stopProgressAnimation() {
  if (progressAnimationTimer === null) return
  window.clearInterval(progressAnimationTimer)
  progressAnimationTimer = null
}

function clampProgress(value: number): number {
  if (!Number.isFinite(value)) return 0
  return Math.min(100, Math.max(0, Math.round(value)))
}

function resolveItemProgress(item: LocalUploadItem): number {
  if (item.status === 'success' || item.status === 'failed') return 1
  if (item.status === 'uploading') return Math.max(0.08, item.stageProgress)
  return item.stageProgress
}

function normalizeUploadStatus(status: string): LocalUploadStatus {
  if (status === 'success' || status === 'failed') return status
  if (status === 'uploading' || status === 'queued' || status === 'cancelled') return status
  return 'pending'
}

function handleUploadProgressEvent(event: RagUploadProgressEvent, files: File[]) {
  const eventName = event.event
  syncBackendUploadProgress(event)
  if (eventName === 'file-start' || eventName === 'file-stage') {
    updateActiveUploadItem(event, files)
    return
  }

  if (eventName === 'file-result') {
    updateResultUploadItem(event, files)
    return
  }

  if (eventName === 'batch-complete') {
    const summary = normalizeUploadSummary(event.summary ?? event)
    if (summary) {
      uploadSummary.value = summary
    }
  }
}

function updateActiveUploadItem(event: RagUploadProgressEvent, files: File[]) {
  const index = resolveEventFileIndex(event, files)
  if (index < 0) return
  const file = files[index]
  if (!file || !uploadItems.value[index]) return
  const stage = normalizeEventStage(event)
  patchUploadItem(index, {
    ...createPendingItem(file, 'uploading', index + 1),
    stage,
    stageProgress: resolveEventFileProgress(event, stage),
    errorMessage: null,
  })
}

function updateResultUploadItem(event: RagUploadProgressEvent, files: File[]) {
  const index = resolveEventFileIndex(event, files)
  if (index < 0) return
  const file = files[index]
  if (!file) return
  const result = normalizeUploadFileResult(event.result)
  const stage = normalizeEventStage(event)
  replaceUploadItem(
    index,
    result
      ? createResultItem(result, file, index + 1, stage, resolveEventFileProgress(event, stage))
      : createFailedItem(file, index + 1, event.message || '后端未返回文件结果')
  )
}

function syncBackendUploadProgress(event: RagUploadProgressEvent) {
  const progressPercent = normalizeOptionalPercent(event.progressPercent ?? event.progress_percent)
  if (progressPercent === null) return
  backendUploadProgressPercent.value = progressPercent
}

function resolveEventFileIndex(event: RagUploadProgressEvent, files: File[]): number {
  const rawIndex = event.fileIndex ?? event.file_index
  if (typeof rawIndex === 'number' && rawIndex > 0) return rawIndex - 1

  const fileName = normalizeString(event.fileName ?? event.file_name)
  if (!fileName) return -1
  return files.findIndex((file) => file.name === fileName)
}

function normalizeEventStage(event: RagUploadProgressEvent): string | undefined {
  const stage = normalizeString(event.stage)
  if (stage) return stage
  return normalizeString(event.message) || undefined
}

function resolveStageProgress(stage?: string): number {
  const normalizedStage = normalizeString(stage)
  if (!normalizedStage) return 0.08
  const matchedStage = UPLOAD_STAGE_PROGRESS.find((item) => normalizedStage.includes(item.keyword))
  return matchedStage?.progress ?? 0.35
}

function resolveResultProgress(status: string, stage?: string): number {
  if (status === 'success' || status === 'failed') return 1
  return resolveStageProgress(stage)
}

function resolveEventFileProgress(event: RagUploadProgressEvent, stage?: string): number {
  const fileProgressPercent = normalizeOptionalPercent(event.fileProgressPercent ?? event.file_progress_percent)
  if (fileProgressPercent !== null) return fileProgressPercent / 100
  return resolveStageProgress(stage)
}

function normalizeUploadFileResult(value: unknown): RagUploadFileResult | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  const fileName = normalizeString(raw.fileName ?? raw.file_name)
  if (!fileName) return null
  return {
    fileName,
    contentType: normalizeString(raw.contentType ?? raw.content_type) || 'application/octet-stream',
    sourceType: normalizeString(raw.sourceType ?? raw.source_type) || 'document',
    ingestSource: normalizeString(raw.ingestSource ?? raw.ingest_source) || 'text_document',
    chunkCount: normalizeNumber(raw.chunkCount ?? raw.chunk_count),
    insertedCount: normalizeNumber(raw.insertedCount ?? raw.inserted_count),
    status: normalizeString(raw.status) || 'failed',
    errorMessage: normalizeNullableString(raw.errorMessage ?? raw.error_message),
  }
}

function normalizeUploadSummary(value: unknown): RagUploadResponse | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  const files = Array.isArray(raw.files)
    ? raw.files.map(normalizeUploadFileResult).filter((item): item is RagUploadFileResult => item !== null)
    : uploadItems.value.map(toRagUploadFileResult)
  return {
    totalFiles: normalizeNumber(raw.totalFiles ?? raw.total_files) || files.length,
    succeededFiles: normalizeNumber(raw.succeededFiles ?? raw.succeeded_files),
    failedFiles: normalizeNumber(raw.failedFiles ?? raw.failed_files),
    inserted: normalizeNumber(raw.inserted),
    files,
  }
}

function normalizeNumber(value: unknown): number {
  const numberValue = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(numberValue) ? numberValue : 0
}

function normalizeOptionalPercent(value: unknown): number | null {
  const numberValue = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(numberValue)) return null
  return clampProgress(numberValue)
}

function normalizeString(value: unknown): string {
  return String(value ?? '').trim()
}

function normalizeNullableString(value: unknown): string | null {
  const text = normalizeString(value)
  return text || null
}

function dedupeFiles(files: File[]): File[] {
  const map = new Map<string, File>()
  for (const file of files) {
    map.set(`${file.name}:${file.size}:${file.lastModified}`, file)
  }
  return Array.from(map.values())
}

function guessSourceType(fileName: string): string {
  const extension = fileName.split('.').pop()?.toLowerCase() ?? ''
  return ['png', 'jpg', 'jpeg', 'webp'].includes(extension) ? 'image' : 'document'
}

function formatFileSize(size: number): string {
  if (size <= 0) return '0 B'
  if (size >= 1024 * 1024) return `${(size / 1024 / 1024).toFixed(2)} MB`
  if (size >= 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${size} B`
}

function sourceTypeLabel(sourceType: string): string {
  return sourceType === 'image' ? '图片' : '文档'
}

function ingestSourceLabel(ingestSource: string): string {
  if (ingestSource === 'image_ocr_text') return 'OCR 入库'
  if (ingestSource === 'text_document') return '文本入库'
  return ingestSource
}

function statusLabel(status: string): string {
  if (status === 'success') return '成功'
  if (status === 'failed') return '失败'
  if (status === 'cancelled') return '已取消'
  if (status === 'queued') return '排队中'
  if (status === 'uploading') return '处理中'
  return '待上传'
}
</script>

<template>
  <section class="knowledge-panel">
    <div class="panel-shell">
      <div class="workspace-layout">
        <section class="panel main-card">
          <div
            class="dropzone"
            :class="{ 'is-drag-over': isDragOver, 'is-disabled': isUploading }"
            @dragenter.prevent="isUploading ? undefined : (isDragOver = true)"
            @dragover.prevent="isUploading ? undefined : (isDragOver = true)"
            @dragleave.prevent="isDragOver = false"
            @drop="onDrop"
          >
            <input
              ref="fileInputRef"
              class="file-input"
              type="file"
              multiple
              :accept="ACCEPT"
              @change="onFileChange"
            />
            <div class="dropzone-icon" aria-hidden="true">
              <CloudUpload :size="30" stroke-width="1.75" />
            </div>
            <h3>拖拽或选择文件</h3>
            <dl class="upload-facts">
              <div v-for="fact in guidanceFacts" :key="fact.label" class="fact-row">
                <span class="fact-icon" aria-hidden="true">
                  <FileText v-if="fact.icon === 'format'" :size="17" stroke-width="1.8" />
                  <ShieldCheck v-else-if="fact.icon === 'limit'" :size="17" stroke-width="1.8" />
                  <Server v-else-if="fact.icon === 'target'" :size="17" stroke-width="1.8" />
                  <ScanText v-else :size="17" stroke-width="1.8" />
                </span>
                <div>
                  <dt>{{ fact.label }}</dt>
                  <dd>{{ fact.value }}</dd>
                </div>
              </div>
            </dl>
          </div>

          <div class="panel-toolbar">
            <button class="primary-btn" type="button" :disabled="isUploading" @click="openFilePicker">
              <FileUp :size="18" stroke-width="1.9" aria-hidden="true" />
              选择文件
            </button>
            <button class="ghost-btn" type="button" :disabled="!hasFiles || isUploading" @click="clearFiles">
              <Trash2 :size="17" stroke-width="1.9" aria-hidden="true" />
              清空列表
            </button>
            <button class="ghost-btn" type="button" :disabled="!hasFiles || isUploading" @click="handleUpload">
              <Play :size="17" stroke-width="1.9" aria-hidden="true" />
              开始上传
            </button>
            <button v-if="isUploading" class="ghost-btn danger-btn" type="button" @click="cancelUpload">
              <CircleX :size="17" stroke-width="1.9" aria-hidden="true" />
              取消上传
            </button>
          </div>

          <div class="compact-bar">
            <p class="compact-summary">{{ compactSummary }}</p>
            <ul class="metric-list">
              <li v-for="metric in compactMetrics" :key="metric.label" class="metric-item">
                <span class="metric-icon" aria-hidden="true">
                  <FileText v-if="metric.icon === 'files'" :size="19" stroke-width="1.8" />
                  <ListChecks v-else-if="metric.icon === 'checks'" :size="19" stroke-width="1.8" />
                  <Blocks v-else :size="19" stroke-width="1.8" />
                </span>
                <span>
                  <span class="metric-label">{{ metric.label }}</span>
                  <strong>{{ metric.value }}</strong>
                </span>
              </li>
            </ul>
          </div>

          <div
            v-if="hasUploadItems"
            class="upload-progress-card"
            :class="{ 'is-uploading': isUploading, 'is-error': uploadPhase === 'error' }"
          >
            <div class="progress-top">
              <div class="progress-copy">
                <span>文件级进度</span>
                <strong>{{ uploadProgressText }}</strong>
              </div>
              <span class="progress-percent">{{ displayedUploadProgressPercent }}%</span>
            </div>
            <div
              class="progress-track"
              role="progressbar"
              aria-label="知识库上传文件级进度"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-valuenow="displayedUploadProgressPercent"
            >
              <span :style="{ width: `${displayedUploadProgressPercent}%` }"></span>
            </div>
            <p class="progress-assist">{{ progressAssistText }}</p>
          </div>

          <p v-if="errorMessage" class="panel-error">{{ errorMessage }}</p>

          <div class="result-block">
            <div class="result-head">
              <h3>{{ resultSectionTitle }}</h3>
              <span v-if="hasUploadItems" class="section-count-chip">{{ uploadItems.length }} 项</span>
            </div>

            <div v-if="!hasUploadItems" class="results-empty" :class="{ 'is-error': uploadPhase === 'error' }">
              <div class="empty-mark" aria-hidden="true">
                <DatabaseZap :size="28" stroke-width="1.75" />
              </div>
              <h3>{{ emptyStateTitle }}</h3>
              <p>{{ emptyStateText }}</p>
            </div>

            <ul v-else class="result-list">
              <li
                v-for="(item, index) in uploadItems"
                :key="`${item.fileName}-${index}`"
                class="result-item"
                :class="`result-${item.status}`"
              >
                <span class="source-icon" aria-hidden="true">
                  <ImageIcon v-if="item.sourceType === 'image'" :size="18" stroke-width="1.8" />
                  <FileText v-else :size="18" stroke-width="1.8" />
                </span>

                <div class="result-main">
                  <div class="result-heading">
                    <div>
                      <p class="file-name">{{ item.fileName }}</p>
                      <p class="file-meta">
                        {{ sourceTypeLabel(item.sourceType) }} · {{ formatFileSize(item.fileSize) }} ·
                        {{ ingestSourceLabel(item.ingestSource) }}
                      </p>
                    </div>
                    <span class="status-pill" :class="`status-${item.status}`">{{ statusLabel(item.status) }}</span>
                  </div>

                  <div class="file-submeta">
                    <span>第 {{ item.order }} 个</span>
                    <span v-if="item.stage">阶段 {{ item.stage }}</span>
                    <span>chunk {{ item.chunkCount }}</span>
                    <span>入库 {{ item.insertedCount }}</span>
                  </div>

                  <div v-if="item.status === 'uploading'" class="file-progress-line" aria-hidden="true">
                    <span></span>
                  </div>

                  <p v-if="item.errorMessage" class="file-error">{{ item.errorMessage }}</p>
                </div>

                <button
                  v-if="uploadPhase === 'ready'"
                  class="remove-btn"
                  type="button"
                  aria-label="删除文件"
                  title="删除文件"
                  @click="removeFile(index)"
                >
                  <Trash2 :size="16" stroke-width="1.9" aria-hidden="true" />
                </button>
              </li>
            </ul>
          </div>
        </section>

      </div>
    </div>
  </section>
</template>

<style scoped src="./KnowledgeBasePanel.css"></style>
<style scoped src="./KnowledgeBasePanel.responsive.css"></style>
