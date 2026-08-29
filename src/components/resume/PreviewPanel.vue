<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useResumeStore } from '@/stores/resume'
import TemplatePickerDialog from '@/components/resume/TemplatePickerDialog.vue'
import {
  RESUME_TEMPLATES,
  getResumeTemplateByKey,
  type ResumeTemplateDefinition,
  type ResumeTemplateKey,
} from '@/templates/resume'
import { generateResumeMarkdown, downloadMarkdown } from '@/services/exportMarkdown'
// author: jf

const store = useResumeStore()
const resumeRef = ref<HTMLElement | null>(null)
const previewScrollRef = ref<HTMLElement | null>(null)
const exporting = ref(false)
const exportProgress = ref(0)
const exportProgressText = ref('')
type ExportQualityMode = 'compressed' | 'hd'
const exportMenuOpen = ref(false)
const exportMenuRef = ref<HTMLElement | null>(null)
const templatePickerOpen = ref(false)

const A4_WIDTH = 794
const A4_RATIO = 297 / 210
const A4_HEIGHT = Math.round(A4_WIDTH * A4_RATIO)
const pageBreaks = ref<number[]>([])
const previewScale = ref(1)
const paperVisualHeight = ref(A4_HEIGHT)

const fallbackTemplate: ResumeTemplateDefinition = getResumeTemplateByKey('default')
const currentTemplate = computed<ResumeTemplateDefinition>(
  () => getResumeTemplateByKey(store.selectedTemplateKey) ?? fallbackTemplate
)
const currentTemplateComponent = computed(() => currentTemplate.value.component)
const a4TemplateLabel = computed(() => `A4 / ${currentTemplate.value.name}`)
const previewWrapperStyle = computed(() => ({
  width: `${Math.round(A4_WIDTH * previewScale.value)}px`,
  height: `${Math.round(paperVisualHeight.value * previewScale.value)}px`,
}))
const previewStageStyle = computed(() => ({
  width: `${A4_WIDTH}px`,
  transform: `scale(${previewScale.value})`,
}))

function waitNextFrame(): Promise<void> {
  return new Promise((resolve) => requestAnimationFrame(() => resolve()))
}

async function setExportProgress(percent: number, text: string) {
  exportProgress.value = Math.max(0, Math.min(100, Math.round(percent)))
  exportProgressText.value = text
  await nextTick()
  await waitNextFrame()
}



function findEffectiveCanvasHeight(canvas: HTMLCanvasElement): number {
  const ctx = canvas.getContext('2d', { willReadFrequently: true })
  if (!ctx) return canvas.height

  const width = canvas.width
  const sampleStepX = Math.max(1, Math.floor(width / 120))

  const rowHasContent = (y: number): boolean => {
    const row = ctx.getImageData(0, y, width, 1).data
    for (let x = 0; x < width; x += sampleStepX) {
      const idx = x * 4
      const alpha = row[idx + 3] ?? 0
      if (alpha === 0) continue
      const r = row[idx] ?? 255
      const g = row[idx + 1] ?? 255
      const b = row[idx + 2] ?? 255
      if (r < 248 || g < 248 || b < 248) return true
    }
    return false
  }

  let roughY = -1
  for (let y = canvas.height - 1; y >= 0; y -= 4) {
    if (rowHasContent(y)) {
      roughY = y
      break
    }
  }

  if (roughY < 0) return 1

  const startY = Math.min(canvas.height - 1, roughY + 3)
  const endY = Math.max(0, roughY - 3)
  for (let y = startY; y >= endY; y -= 1) {
    if (rowHasContent(y)) return Math.min(canvas.height, y + 4)
  }

  return Math.min(canvas.height, roughY + 4)
}

function updatePageBreaks() {
  if (!resumeRef.value) return
  const contentHeight = resumeRef.value.scrollHeight
  const pageHeight = A4_HEIGHT
  paperVisualHeight.value = Math.max(A4_HEIGHT, contentHeight)
  const breaks: number[] = []
  const totalPages = Math.max(1, Math.ceil((contentHeight - 1) / pageHeight))
  const resumeRect = resumeRef.value.getBoundingClientRect()
  const avoidElements = Array.from(
    resumeRef.value.querySelectorAll<HTMLElement>('.section-title, .entry-head, .entry-rich li, .entry-rich p, .meta-line, .entry')
  )

  let currentBreak = pageHeight
  for (let i = 1; i < totalPages; i += 1) {
    let safeBreak = currentBreak
    for (const el of avoidElements) {
      const rect = el.getBoundingClientRect()
      const top = rect.top - resumeRect.top
      const bottom = rect.bottom - resumeRect.top
      if (top < currentBreak && bottom > currentBreak && currentBreak - top < pageHeight * 0.35) {
        safeBreak = Math.min(safeBreak, Math.floor(top) - 4)
      }
    }
    breaks.push(safeBreak)
    currentBreak = safeBreak + pageHeight
  }
  pageBreaks.value = breaks
}

function updatePreviewScale() {
  const scrollEl = previewScrollRef.value
  const viewportWidth = scrollEl?.clientWidth || A4_WIDTH
  const styles = scrollEl ? window.getComputedStyle(scrollEl) : null
  const horizontalPadding =
    (Number.parseFloat(styles?.paddingLeft ?? '0') || 0) +
    (Number.parseFloat(styles?.paddingRight ?? '0') || 0)
  const contentWidth = Math.max(0, viewportWidth - horizontalPadding)
  const nextScale = Math.min(1, Math.max(0.36, contentWidth / A4_WIDTH))
  previewScale.value = Math.floor(nextScale * 1000) / 1000
}

function openTemplatePicker() {
  templatePickerOpen.value = true
  exportMenuOpen.value = false
}

function chooseTemplate(key: ResumeTemplateKey) {
  store.setTemplate(key)
  templatePickerOpen.value = false
}

let resizeObserver: ResizeObserver | null = null
let previewResizeObserver: ResizeObserver | null = null
let previewScaleFrame: number | null = null

function schedulePreviewScaleUpdate() {
  if (previewScaleFrame !== null) return
  previewScaleFrame = requestAnimationFrame(() => {
    previewScaleFrame = null
    updatePreviewScale()
  })
}

onMounted(() => {
  nextTick(() => {
    updatePreviewScale()
    updatePageBreaks()
  })
  if (resumeRef.value) {
    resizeObserver = new ResizeObserver(() => updatePageBreaks())
    resizeObserver.observe(resumeRef.value)
  }
  if (previewScrollRef.value) {
    previewResizeObserver = new ResizeObserver(() => schedulePreviewScaleUpdate())
    previewResizeObserver.observe(previewScrollRef.value)
  }
  window.addEventListener('resize', schedulePreviewScaleUpdate)
  document.addEventListener('mousedown', handleDocumentPointerDown)
})

watch(
  () => [
    JSON.stringify(store.modules),
    JSON.stringify(store.basicInfo),
    JSON.stringify(store.educationList),
    store.skills,
    JSON.stringify(store.workList),
    JSON.stringify(store.projectList),
    JSON.stringify(store.awardList),
    store.selfIntro,
    store.selectedTemplateKey,
  ],
  () => {
    nextTick(() => {
      updatePreviewScale()
      updatePageBreaks()
    })
  }
)

onUnmounted(() => {
  resizeObserver?.disconnect()
  previewResizeObserver?.disconnect()
  if (previewScaleFrame !== null) cancelAnimationFrame(previewScaleFrame)
  window.removeEventListener('resize', schedulePreviewScaleUpdate)
  document.removeEventListener('mousedown', handleDocumentPointerDown)
})

function handleExportTriggerClick() {
  if (exporting.value) return
  exportMenuOpen.value = !exportMenuOpen.value
}

function handleExportTriggerEnter() {
  if (exporting.value) return
  exportMenuOpen.value = true
}

function handleDocumentPointerDown(event: MouseEvent) {
  const target = event.target as Node | null
  if (!target || !exportMenuRef.value) return
  if (!exportMenuRef.value.contains(target)) {
    exportMenuOpen.value = false
  }
}

function handleExportMarkdown() {
  exportMenuOpen.value = false
  const md = generateResumeMarkdown(store)
  const name = store.basicInfo.name?.trim() || '简历'
  downloadMarkdown(`${name}_简历.md`, md)
}

function handleExportJson() {
  exportMenuOpen.value = false
  const name = store.basicInfo.name?.trim() || '简历'
  const blob = new Blob([store.exportResumeData()], {
    type: 'application/json;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${name}_简历.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

async function exportPDF(mode: ExportQualityMode) {
  if (!resumeRef.value) return
  exporting.value = true
  exportMenuOpen.value = false
  exportProgress.value = 0
  exportProgressText.value = '准备导出...'
  const isHdMode = mode === 'hd'
  const sourceNode = resumeRef.value
  const exportHost = document.createElement('div')
  exportHost.style.position = 'fixed'
  exportHost.style.left = '-10000px'
  exportHost.style.top = '0'
  exportHost.style.width = `${A4_WIDTH}px`
  exportHost.style.pointerEvents = 'none'
  exportHost.style.opacity = '0'
  exportHost.style.zIndex = '-1'

  const exportNode = sourceNode.cloneNode(true) as HTMLElement
  exportNode.classList.add('pdf-exporting')
  exportNode.style.width = `${A4_WIDTH}px`
  exportNode.style.minHeight = '0'
  exportNode.style.height = 'auto'
  exportNode.style.margin = '0'
  exportNode.style.overflow = 'hidden'

  exportHost.appendChild(exportNode)
  document.body.appendChild(exportHost)
  const resumePaperBackground = window
    .getComputedStyle(document.documentElement)
    .getPropertyValue('--resume-paper-background')
    .trim()

  try {
    await setExportProgress(8, '准备导出资源...')
    await document.fonts?.ready
    await setExportProgress(18, '加载导出引擎...')
    const [{ default: html2canvas }, { jsPDF }] = await Promise.all([import('html2canvas-pro'), import('jspdf')])
    await setExportProgress(36, '正在渲染简历画布...')
    const exportScale = isHdMode ? Math.min(4, Math.max(3, window.devicePixelRatio || 1)) : 2
    const canvas = await html2canvas(exportNode, {
      scale: exportScale,
      useCORS: true,
      width: A4_WIDTH,
      windowWidth: A4_WIDTH,
      backgroundColor: resumePaperBackground,
      scrollX: 0,
      scrollY: 0,
    })
    await setExportProgress(68, '正在分页生成 PDF...')

    const pdf = new jsPDF({
      unit: 'mm',
      format: 'a4',
      orientation: 'portrait',
      compress: !isHdMode,
    })

    const pagePixelHeight = Math.round(canvas.width * A4_RATIO)
    const effectiveHeight = findEffectiveCanvasHeight(canvas)
    const totalPages = Math.max(1, Math.ceil(effectiveHeight / pagePixelHeight))
    let offsetY = 0
    let pageIndex = 0

    const exportRect = exportNode.getBoundingClientRect()
    const avoidElements = Array.from(
      exportNode.querySelectorAll<HTMLElement>(
        '.section-title, .entry-head, .entry-rich li, .entry-rich p, .meta-line, .entry'
      )
    )

    while (offsetY < effectiveHeight - 1) {
      const remainingHeight = effectiveHeight - offsetY
      let sliceHeight = Math.min(pagePixelHeight, remainingHeight)
      if (offsetY + sliceHeight < effectiveHeight - 1) {
        const idealCutDomY = (offsetY + sliceHeight) / exportScale
        let safeCutDomY = idealCutDomY
        for (const el of avoidElements) {
          const rect = el.getBoundingClientRect()
          const top = rect.top - exportRect.top
          const bottom = rect.bottom - exportRect.top
          if (top < idealCutDomY && bottom > idealCutDomY && idealCutDomY - top < A4_HEIGHT * 0.35) {
            safeCutDomY = Math.min(safeCutDomY, top - 4)
          }
        }
        sliceHeight = Math.max(10, Math.round(safeCutDomY * exportScale) - offsetY)
      }
      if (sliceHeight <= 2) break

      const pageCanvas = document.createElement('canvas')
      pageCanvas.width = canvas.width
      pageCanvas.height = sliceHeight
      const ctx = pageCanvas.getContext('2d')
      if (!ctx) break
      ctx.imageSmoothingEnabled = true
      ctx.imageSmoothingQuality = 'high'
      ctx.fillStyle = resumePaperBackground
      ctx.fillRect(0, 0, pageCanvas.width, pageCanvas.height)
      ctx.drawImage(canvas, 0, offsetY, canvas.width, sliceHeight, 0, 0, canvas.width, sliceHeight)

      const imgData = isHdMode ? pageCanvas.toDataURL('image/png') : pageCanvas.toDataURL('image/jpeg', 0.92)
      const imgWidthMm = 210
      const imgHeightMm = (sliceHeight / canvas.width) * imgWidthMm

      if (pageIndex > 0) pdf.addPage('a4', 'portrait')
      pdf.addImage(imgData, isHdMode ? 'PNG' : 'JPEG', 0, 0, imgWidthMm, imgHeightMm, undefined, isHdMode ? 'NONE' : 'FAST')
      const pageProgress = 68 + Math.round((Math.min(pageIndex + 1, totalPages) / totalPages) * 28)
      await setExportProgress(pageProgress, `正在写入第 ${Math.min(pageIndex + 1, totalPages)}/${totalPages} 页...`)

      offsetY += sliceHeight
      pageIndex += 1
    }

    await setExportProgress(98, '正在保存文件...')
    pdf.save(`${store.basicInfo.name || '简历'}_resume.pdf`)
    await setExportProgress(100, '导出完成')
  } catch (err) {
    console.error('PDF 导出失败:', err)
  } finally {
    exportHost.remove()
    exportProgress.value = 0
    exportProgressText.value = ''
    exporting.value = false
  }
}
</script>

<template>
  <aside class="preview-panel">
    <div class="preview-top">
      <div class="preview-title-row">
        <button class="template-trigger" @click="openTemplatePicker">
          <span class="template-trigger-label">切换模板</span>
          <span class="template-trigger-name">{{ currentTemplate.name }}</span>
          <span class="template-trigger-arrow">▾</span>
        </button>
        <span class="a4-badge">{{ a4TemplateLabel }}</span>
      </div>
      <div
        ref="exportMenuRef"
        class="export-actions export-dropdown"
        @mouseenter="handleExportTriggerEnter"
      >
        <button class="btn-export" :disabled="exporting" @click="handleExportTriggerClick">
          {{ exporting ? '导出中...' : '导出' }}
        </button>
        <div v-if="exportMenuOpen && !exporting" class="export-menu">
          <button class="export-menu-item" @click="exportPDF('hd')">导出高清 PDF</button>
          <button class="export-menu-item" @click="exportPDF('compressed')">导出压缩 PDF</button>
          <button class="export-menu-item" @click="handleExportMarkdown">导出 Markdown</button>
          <button class="export-menu-item" @click="handleExportJson">导出 JSON 进度</button>
        </div>
      </div>
    </div>
    <div v-if="exporting" class="export-progress">
      <div class="export-progress-head">
        <span class="export-progress-text">{{ exportProgressText || '导出中...' }}</span>
        <span class="export-progress-percent">{{ exportProgress }}%</span>
      </div>
      <div class="export-progress-track">
        <span class="export-progress-fill" :style="{ width: `${exportProgress}%` }"></span>
      </div>
    </div>

    <TemplatePickerDialog
      v-model="templatePickerOpen"
      :templates="RESUME_TEMPLATES"
      :selected-key="store.selectedTemplateKey"
      @select="chooseTemplate"
    />

    <div ref="previewScrollRef" class="preview-scroll">
      <div class="paper-wrapper" :style="previewWrapperStyle">
        <div class="paper-scale-stage" :style="previewStageStyle">
          <div ref="resumeRef" class="paper" :style="{ width: `${A4_WIDTH}px`, minHeight: `${A4_HEIGHT}px` }">
            <component :is="currentTemplateComponent" />
          </div>

          <div v-for="(pos, idx) in pageBreaks" :key="idx" class="page-line" :style="{ top: `${pos}px` }">
            <span>第{{ idx + 2 }}页</span>
          </div>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.preview-panel {
  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0;
  border: 0;
  background: transparent;
}

.preview-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.preview-title-row {
  min-width: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.template-trigger,
.a4-badge,
.btn-export {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.template-trigger {
  height: 28px;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid var(--border-color);
  background: var(--surface-soft);
  color: var(--text-primary);
  cursor: pointer;
}

.template-trigger:hover {
  border-color: var(--primary-500);
  background: var(--primary-50);
  color: var(--primary-500);
}

.template-trigger-label {
  color: var(--primary-500);
}

.template-trigger-name {
  max-width: 150px;
  overflow: hidden;
  color: var(--text-primary);
  text-overflow: ellipsis;
}

.template-trigger-arrow {
  color: var(--text-secondary);
}

.a4-badge {
  height: 28px;
  padding: 0 10px;
  border: 1px solid var(--border-color);
  background: var(--surface-base);
  color: var(--text-secondary);
}

.btn-export {
  height: 32px;
  padding: 0 13px;
  border: 1px solid var(--primary-500);
  background: var(--primary-500);
  color: var(--text-inverse);
  cursor: pointer;
}

.btn-export:hover:not(:disabled) {
  background: var(--primary-600);
}

.btn-export:disabled {
  opacity: 0.7;
  cursor: wait;
}

.export-actions {
  display: flex;
  align-items: center;
  flex: 0 0 auto;
}

.export-dropdown {
  position: relative;
}

.export-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 20;
  min-width: 152px;
  padding: 6px;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  background: var(--surface-base);
  box-shadow: var(--shadow-xl);
}

.export-menu-item {
  width: 100%;
  min-height: 34px;
  padding: 0 10px;
  border: 0;
  border-radius: 10px;
  background: var(--surface-base);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 700;
  text-align: left;
  cursor: pointer;
}

.export-menu-item:hover {
  background: var(--primary-50);
  color: var(--primary-500);
}

.export-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  background: var(--surface-soft);
}

.export-progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.export-progress-text,
.export-progress-percent {
  font-size: 12px;
  font-weight: 700;
}

.export-progress-text {
  color: var(--text-secondary);
}

.export-progress-percent {
  color: var(--text-primary);
}

.export-progress-track {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--border-soft);
}

.export-progress-fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--primary-500);
  transition: width 0.18s ease;
}

.preview-scroll {
  flex: 1;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  scrollbar-gutter: stable;
  padding: 0;
  border: 0;
  background: var(--resume-paper-background);
}

.paper-wrapper {
  position: relative;
  margin: 0 auto;
  padding-bottom: 8px;
}

.paper-scale-stage {
  position: absolute;
  left: 0;
  top: 0;
  transform-origin: top left;
}

.paper {
  box-sizing: border-box;
  background: var(--resume-paper-background);
  border: 0;
  color: var(--resume-paper-ink);
}

.paper.pdf-exporting {
  box-shadow: none;
  border: none;
  border-radius: 0;
  min-height: 0 !important;
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif !important;
}

.paper.pdf-exporting * {
  font-family: inherit !important;
}




.page-line {
  position: absolute;
  left: 16px;
  right: 16px;
  height: 0;
  pointer-events: none;
  z-index: 2;
}

.page-line::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: 0;
  border-top: 1px dashed var(--primary-500);
}

.page-line span {
  position: absolute;
  left: 50%;
  top: 0;
  transform: translate(-50%, -50%);
  color: var(--primary-500);
  font-size: 10px;
  font-weight: 600;
  background: var(--bg-preview);
  padding: 0 4px;
}

@media (max-width: 760px) {
  .preview-panel {
    width: 100%;
    max-width: none;
    flex: 1 1 auto;
    height: 100%;
    padding: 6px 0 0;
    border: 0;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
    gap: 6px;
  }

  .preview-top {
    align-items: stretch;
    flex-direction: column;
    padding: 0 8px;
  }

  .preview-title-row {
    flex-wrap: wrap;
  }

  .template-trigger {
    flex: 1 1 180px;
    justify-content: space-between;
    height: 34px;
  }

  .template-trigger-name {
    max-width: 140px;
  }

  .a4-badge {
    height: 26px;
  }

  .export-actions,
  .btn-export {
    width: 100%;
  }

  .btn-export {
    height: 34px;
  }

  .export-menu {
    left: 0;
    right: 0;
  }

  .export-menu-item {
    min-height: 34px;
  }

  .preview-scroll {
    overflow-x: hidden;
    overflow-y: auto;
    scrollbar-width: none;
    scrollbar-gutter: auto;
    padding: 0 8px;
  }

  .preview-scroll::-webkit-scrollbar {
    display: none;
  }

  .paper-wrapper {
    padding-bottom: 0;
  }

}
</style>
