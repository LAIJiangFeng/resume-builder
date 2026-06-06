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
// 预览分页线按用户实测的导出分页位置向上校准。
const PDF_PAGE_BREAK_PREVIEW_OFFSET = 16
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

function prepareResumeTemplatePdfAlignment(exportNode: HTMLElement) {
  const defaultTemplate = exportNode.querySelector<HTMLElement>('.resume-template-default')

  // html2canvas 对原生 marker 和行高基线的处理不稳定，导出副本用真实绝对定位标记保证视觉对齐。
  const sectionTitles = defaultTemplate?.querySelectorAll<HTMLElement>('.section-title') ?? []
  sectionTitles.forEach((title) => {
    if (title.querySelector(':scope > .pdf-export-title-text')) return

    const titleText = document.createElement('span')
    titleText.className = 'pdf-export-title-text'
    while (title.firstChild) {
      titleText.appendChild(title.firstChild)
    }
    title.appendChild(titleText)
  })

  const metaIcons = exportNode.querySelectorAll<SVGSVGElement>('.meta-item > .meta-icon-svg')
  metaIcons.forEach((icon) => {
    if (icon.parentElement?.classList.contains('pdf-export-meta-icon-box')) return
    const metaItem = icon.parentElement
    if (!(metaItem instanceof HTMLElement)) return

    const iconBox = document.createElement('span')
    iconBox.className = 'pdf-export-meta-icon-box'
    iconBox.setAttribute('aria-hidden', 'true')
    metaItem.classList.add('pdf-export-meta-item')
    metaItem.insertBefore(iconBox, icon)
    iconBox.appendChild(icon)

    Array.from(metaItem.childNodes).forEach((node) => {
      if (node === iconBox) return
      if (node instanceof HTMLElement) {
        node.classList.add('pdf-export-meta-text')
        return
      }

      if (node.nodeType !== Node.TEXT_NODE || !node.textContent?.trim()) return
      const textBox = document.createElement('span')
      textBox.className = 'pdf-export-meta-text'
      textBox.textContent = node.textContent
      metaItem.replaceChild(textBox, node)
    })
  })

  const listItems = defaultTemplate?.querySelectorAll<HTMLElement>('.entry-rich ul > li, .entry-rich ol > li') ?? []
  listItems.forEach((item) => {
    if (item.querySelector(':scope > .pdf-export-inline-marker')) return

    const parent = item.parentElement
    if (!parent) return

    const marker = document.createElement('span')
    marker.className = 'pdf-export-inline-marker'
    marker.setAttribute('aria-hidden', 'true')

    if (parent.tagName === 'OL') {
      marker.classList.add('pdf-export-inline-marker-number')
      const siblings = Array.from(parent.children).filter((node): node is HTMLElement => node instanceof HTMLElement && node.tagName === 'LI')
      const index = Math.max(0, siblings.indexOf(item))
      const start = Number.parseInt(parent.getAttribute('start') || '1', 10)
      const explicitValue = Number.parseInt(item.getAttribute('value') || '', 10)
      const markerValue = Number.isFinite(explicitValue) ? explicitValue : (Number.isFinite(start) ? start : 1) + index
      marker.textContent = `${markerValue}.`
    } else {
      marker.classList.add('pdf-export-inline-marker-bullet')
    }

    item.classList.add('pdf-export-list-item')
    item.insertBefore(marker, item.firstChild)
  })
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
  for (let i = 1; i < totalPages; i += 1) {
    breaks.push(i * pageHeight - PDF_PAGE_BREAK_PREVIEW_OFFSET)
  }
  pageBreaks.value = breaks
}

function updatePreviewScale() {
  const viewportWidth = previewScrollRef.value?.clientWidth || A4_WIDTH
  const nextScale = Math.min(1, Math.max(0.36, (viewportWidth - 8) / A4_WIDTH))
  previewScale.value = Number(nextScale.toFixed(3))
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
    previewResizeObserver = new ResizeObserver(() => updatePreviewScale())
    previewResizeObserver.observe(previewScrollRef.value)
  }
  window.addEventListener('resize', updatePreviewScale)
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
  window.removeEventListener('resize', updatePreviewScale)
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
  prepareResumeTemplatePdfAlignment(exportNode)

  try {
    await setExportProgress(8, '准备导出资源...')
    await document.fonts?.ready
    await setExportProgress(18, '加载导出引擎...')
    const [{ default: html2canvas }, { jsPDF }] = await Promise.all([import('html2canvas'), import('jspdf')])
    await setExportProgress(36, '正在渲染简历画布...')
    const exportScale = isHdMode ? Math.min(4, Math.max(3, window.devicePixelRatio || 1)) : 2
    const canvas = await html2canvas(exportNode, {
      scale: exportScale,
      useCORS: true,
      width: A4_WIDTH,
      windowWidth: A4_WIDTH,
      backgroundColor: '#ffffff',
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

    while (offsetY < effectiveHeight - 1) {
      const remainingHeight = effectiveHeight - offsetY
      const sliceHeight = Math.min(pagePixelHeight, remainingHeight)
      if (sliceHeight <= 2) break

      const pageCanvas = document.createElement('canvas')
      pageCanvas.width = canvas.width
      pageCanvas.height = sliceHeight
      const ctx = pageCanvas.getContext('2d')
      if (!ctx) break
      ctx.imageSmoothingEnabled = true
      ctx.imageSmoothingQuality = 'high'
      ctx.fillStyle = '#ffffff'
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
    console.error('PDF export failed:', err)
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
        <span class="preview-title">实时预览</span>
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
  width: clamp(320px, 46%, 812px);
  max-width: 812px;
  min-width: 0;
  flex: 0 1 clamp(320px, 46%, 812px);
  height: 100%;
  border-left: 1px solid #e4d8cb;
  background: #efe7dc;
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.preview-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.preview-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.preview-title {
  color: #2d2521;
  font-size: 16px;
  font-weight: 700;
}

.template-trigger {
  height: 30px;
  padding: 0 10px 0 8px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border-radius: 8px;
  border: 1px solid #e0d2c1;
  background: #fff;
  color: #2d2521;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  outline: none;
  box-shadow: 0 1px 0 rgba(45, 37, 33, 0.06);
  transition: background-color 0.12s ease, border-color 0.12s ease, box-shadow 0.12s ease;
}

.template-trigger:hover {
  border-color: #cdbba7;
  background: #faf6f0;
  box-shadow: 0 4px 12px rgba(45, 37, 33, 0.1);
}

.template-trigger-label {
  height: 20px;
  padding: 0 6px;
  border-radius: 6px;
  background: #2d2521;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
}

.template-trigger-name {
  color: #2d2521;
  font-size: 12px;
  font-weight: 700;
  max-width: 180px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.template-trigger-arrow {
  color: #7b6a5b;
  font-size: 11px;
  line-height: 1;
}

.a4-badge {
  height: 24px;
  padding: 0 8px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid #e9ded0;
  color: #7b6a5b;
  font-size: 11px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
}

.btn-export {
  border: none;
  height: 30px;
  padding: 0 10px;
  border-radius: 8px;
  background: #2d2521;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
}

.btn-export:disabled {
  opacity: 0.7;
  cursor: wait;
}

.export-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.export-dropdown {
  position: relative;
}

.export-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 124px;
  padding: 4px;
  border-radius: 8px;
  border: 1px solid #e9ded0;
  background: #fff;
  box-shadow: 0 10px 20px rgba(45, 37, 33, 0.14);
  z-index: 12;
}

.export-menu-item {
  width: 100%;
  border: none;
  border-radius: 6px;
  background: #fff;
  color: #2d2521;
  font-size: 12px;
  font-weight: 600;
  text-align: left;
  padding: 7px 8px;
  cursor: pointer;
  transition: background-color 0.12s ease, color 0.12s ease;
}

.export-menu-item:hover {
  background: #eadccf;
  color: #1f1916;
}

.export-progress {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 10px;
  border: 1px solid #e9ded0;
  border-radius: 8px;
  background: #fff8f2;
}

.export-progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.export-progress-text {
  font-size: 12px;
  color: #7b6a5b;
  font-weight: 600;
}

.export-progress-percent {
  font-size: 12px;
  color: #2d2521;
  font-weight: 700;
}

.export-progress-track {
  position: relative;
  width: 100%;
  height: 6px;
  border-radius: 999px;
  background: #eedfce;
  overflow: hidden;
}

.export-progress-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #d97745 0%, #c96a3b 100%);
  transition: width 0.18s ease;
}

.preview-scroll {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 0;
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
  background: #fff;
  border: 1px solid #d8dde6;
  border-radius: 4px;
  color: #000;
  box-shadow: 0 12px 24px rgba(45, 37, 33, 0.1);
}

.paper.pdf-exporting {
  box-shadow: none;
  border: none;
  border-radius: 0;
  min-height: 0 !important;
}

:global(.paper.pdf-exporting .resume-template-default .section-title) {
  display: flex;
  align-items: center;
  line-height: 1;
}

:global(.paper.pdf-exporting .resume-template-default .pdf-export-title-text) {
  display: inline-block;
  line-height: 1;
  transform: translateY(-10px);
}

:global(.paper.pdf-exporting .pdf-export-meta-item) {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 20px;
  line-height: 20px;
}

:global(.paper.pdf-exporting .pdf-export-meta-text) {
  display: inline-block;
  line-height: 20px;
}

:global(.paper.pdf-exporting .pdf-export-meta-icon-box) {
  box-sizing: border-box;
  position: relative;
  top: 7px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 14px;
  width: 14px;
  min-width: 14px;
  height: 20px;
  padding: 0;
  line-height: 20px;
  overflow: visible;
}

:global(.paper.pdf-exporting .pdf-export-meta-icon-box .meta-icon-svg) {
  margin-top: 0;
  transform: none;
}

:global(.paper.pdf-exporting .resume-template-default .entry-rich ol) {
  list-style: none;
}

:global(.paper.pdf-exporting .resume-template-default .entry-rich ul li.pdf-export-list-item::before) {
  content: none;
}

:global(.paper.pdf-exporting .resume-template-default .entry-rich .pdf-export-list-item) {
  position: relative;
}

:global(.paper.pdf-exporting .resume-template-default .pdf-export-inline-marker) {
  position: absolute;
  display: block;
  pointer-events: none;
  color: currentColor;
  font-family: inherit;
  font-variant-numeric: tabular-nums;
}

:global(.paper.pdf-exporting .resume-template-default .pdf-export-inline-marker-number) {
  top: 0;
  left: -1.15em;
  min-width: 1em;
  height: 1.75em;
  line-height: 1.75;
  text-align: right;
  transform: none;
  font-size: 1em;
  font-weight: inherit;
}

:global(.paper.pdf-exporting .resume-template-default .pdf-export-inline-marker-bullet) {
  top: 1.45em;
  left: 2px;
  width: 5px;
  height: 5px;
  transform: translateY(-50%);
  border-radius: 50%;
  background: currentColor;
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
  border-top: 1px dashed #d97745;
}

.page-line span {
  position: absolute;
  left: 50%;
  top: 0;
  transform: translate(-50%, -50%);
  color: #d97745;
  font-size: 10px;
  font-weight: 600;
  background: #efe7dc;
  padding: 0 4px;
}

@media (max-width: 760px) {
  .preview-panel {
    width: 100%;
    max-width: none;
    flex: 1 1 auto;
    height: 100%;
    border-left: none;
    padding: 6px 7px 8px;
    gap: 7px;
  }

  .preview-top {
    align-items: stretch;
    flex-direction: column;
  }

  .preview-title-row {
    flex-wrap: wrap;
  }

  .preview-title {
    width: 100%;
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
    overflow: auto;
    padding: 2px 0 0;
  }

  .paper-wrapper {
    padding-bottom: 0;
  }
}
</style>
