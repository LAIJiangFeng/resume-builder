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
type PdfRenderMode = 'pro' | 'foreign-object' | 'calibrated'

interface ExportElementPair {
  sourceElement: Element
  exportElement: Element
}

interface ResumeExportClone {
  exportHost: HTMLElement
  exportNode: HTMLElement
  elementPairs: ExportElementPair[]
}

interface PageBreakElementMapping {
  sourceTop: number
  sourceBottom: number
  exportTop: number
  exportBottom: number
}

const exportMenuOpen = ref(false)
const exportMenuRef = ref<HTMLElement | null>(null)
const templatePickerOpen = ref(false)

const A4_WIDTH = 794
const A4_RATIO = 297 / 210
const A4_HEIGHT = Math.round(A4_WIDTH * A4_RATIO)
const PDF_RENDER_MODE_FALLBACKS: Record<PdfRenderMode, PdfRenderMode | null> = {
  pro: 'foreign-object',
  'foreign-object': 'calibrated',
  calibrated: null,
}
const PDF_RENDER_MODE_LABELS: Record<PdfRenderMode, string> = {
  pro: '增强解析器',
  'foreign-object': '浏览器原生兼容',
  calibrated: '校准兼容',
}
let pdfRenderMode: PdfRenderMode = 'pro'
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
  // 校准兼容模式不用原生 marker，改用真实绝对定位标记保证视觉对齐。
  const sectionTitles = exportNode.querySelectorAll<HTMLElement>(
    '.resume-template-default .section-title, .resume-template-blue-linear .section-title',
  )
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

  const listItems = exportNode.querySelectorAll<HTMLElement>(
    [
      '.resume-template-default .entry-rich ul > li',
      '.resume-template-default .entry-rich ol > li',
      '.resume-template-blue-linear .entry-rich ul > li',
      '.resume-template-blue-linear .entry-rich ol > li',
    ].join(', '),
  )
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

function createResumeExportClone(sourceNode: HTMLElement, renderMode: PdfRenderMode): ResumeExportClone {
  const sourceElements: Element[] = [sourceNode, ...sourceNode.querySelectorAll('*')]
  const exportHost = document.createElement('div')
  exportHost.style.position = 'fixed'
  exportHost.style.left = '0'
  exportHost.style.top = '0'
  exportHost.style.width = `${A4_WIDTH}px`
  exportHost.style.pointerEvents = 'none'
  exportHost.style.opacity = '0'
  exportHost.style.zIndex = '-1'

  const exportNode = sourceNode.cloneNode(true) as HTMLElement
  const exportElements: Element[] = [exportNode, ...exportNode.querySelectorAll('*')]
  if (renderMode === 'calibrated') exportNode.classList.add('pdf-exporting')
  exportNode.style.width = `${A4_WIDTH}px`
  exportNode.style.minHeight = '0'
  exportNode.style.height = 'auto'
  exportNode.style.margin = '0'
  if (renderMode === 'calibrated') exportNode.style.overflow = 'hidden'

  exportHost.appendChild(exportNode)
  document.body.appendChild(exportHost)
  try {
    if (renderMode === 'calibrated') prepareResumeTemplatePdfAlignment(exportNode)
  } catch (error) {
    exportHost.remove()
    throw error
  }

  const pairCount = Math.min(sourceElements.length, exportElements.length)
  const elementPairs: ExportElementPair[] = []
  for (let index = 0; index < pairCount; index += 1) {
    const sourceElement = sourceElements[index]
    const exportElement = exportElements[index]
    if (!sourceElement || !exportElement) continue
    elementPairs.push({ sourceElement, exportElement })
  }

  return { exportHost, exportNode, elementPairs }
}

function collectPageBreakElementMappings(
  sourceNode: HTMLElement,
  exportNode: HTMLElement,
  elementPairs: ExportElementPair[],
): PageBreakElementMapping[] {
  const sourceRootRect = sourceNode.getBoundingClientRect()
  const exportRootRect = exportNode.getBoundingClientRect()
  const sourceScale = sourceNode.offsetWidth > 0 ? sourceRootRect.width / sourceNode.offsetWidth : 1
  const exportScale = exportNode.offsetWidth > 0 ? exportRootRect.width / exportNode.offsetWidth : 1
  if (sourceScale <= 0 || exportScale <= 0) return []

  const mappings: PageBreakElementMapping[] = []
  elementPairs.forEach(({ sourceElement, exportElement }) => {
    if (sourceElement === sourceNode || exportElement === exportNode) return
    const sourceRect = sourceElement.getBoundingClientRect()
    const exportRect = exportElement.getBoundingClientRect()
    if (sourceRect.height <= 0 || exportRect.height <= 0) return

    mappings.push({
      sourceTop: (sourceRect.top - sourceRootRect.top) / sourceScale,
      sourceBottom: (sourceRect.bottom - sourceRootRect.top) / sourceScale,
      exportTop: (exportRect.top - exportRootRect.top) / exportScale,
      exportBottom: (exportRect.bottom - exportRootRect.top) / exportScale,
    })
  })
  return mappings
}

function mapExportBoundaryToPreview(boundary: number, mappings: PageBreakElementMapping[]): number {
  const containingMappings = mappings
    .filter((mapping) =>
      mapping.exportTop <= boundary &&
      mapping.exportBottom >= boundary &&
      mapping.exportBottom - mapping.exportTop <= A4_HEIGHT,
    )
    .sort((left, right) =>
      (left.exportBottom - left.exportTop) - (right.exportBottom - right.exportTop),
    )
  const containingMapping = containingMappings[0]
  if (containingMapping) {
    const exportHeight = containingMapping.exportBottom - containingMapping.exportTop
    const sourceHeight = containingMapping.sourceBottom - containingMapping.sourceTop
    const progress = exportHeight > 0 ? (boundary - containingMapping.exportTop) / exportHeight : 0
    return containingMapping.sourceTop + Math.max(0, Math.min(1, progress)) * sourceHeight
  }

  let mappedBoundary = boundary
  let nearestDistance = Number.POSITIVE_INFINITY
  mappings.forEach((mapping) => {
    const anchors: Array<[number, number]> = [
      [mapping.exportTop, mapping.sourceTop],
      [mapping.exportBottom, mapping.sourceBottom],
    ]
    anchors.forEach(([exportAnchor, sourceAnchor]) => {
      const distance = Math.abs(boundary - exportAnchor)
      if (distance >= nearestDistance) return
      nearestDistance = distance
      mappedBoundary = boundary + sourceAnchor - exportAnchor
    })
  })
  return mappedBoundary
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

function createUnmappedPageBreaks(contentHeight: number): number[] {
  const breaks: number[] = []
  const totalPages = Math.max(1, Math.ceil((contentHeight - 1) / A4_HEIGHT))
  for (let pageIndex = 1; pageIndex < totalPages; pageIndex += 1) {
    breaks.push(pageIndex * A4_HEIGHT)
  }
  return breaks
}

function updatePageBreaks() {
  const sourceNode = resumeRef.value
  if (!sourceNode) return

  const sourceContentHeight = sourceNode.scrollHeight
  paperVisualHeight.value = Math.max(A4_HEIGHT, sourceContentHeight)
  let exportClone: ResumeExportClone | null = null

  try {
    exportClone = createResumeExportClone(sourceNode, pdfRenderMode)
    const exportContentHeight = Math.max(A4_HEIGHT, exportClone.exportNode.scrollHeight)
    const totalPages = Math.max(1, Math.ceil((exportContentHeight - 1) / A4_HEIGHT))
    const mappings = collectPageBreakElementMappings(
      sourceNode,
      exportClone.exportNode,
      exportClone.elementPairs,
    )
    const breaks: number[] = []
    for (let pageIndex = 1; pageIndex < totalPages; pageIndex += 1) {
      const exportBoundary = pageIndex * A4_HEIGHT
      const mappedBoundary = mappings.length
        ? mapExportBoundaryToPreview(exportBoundary, mappings)
        : exportBoundary
      const previousBoundary = breaks[breaks.length - 1] ?? 0
      const previewBoundary = Math.max(
        Math.min(sourceContentHeight, previousBoundary + 1),
        Math.min(sourceContentHeight, Math.round(mappedBoundary)),
      )
      breaks.push(previewBoundary)
    }
    pageBreaks.value = breaks
  } catch {
    pageBreaks.value = createUnmappedPageBreaks(sourceContentHeight)
  } finally {
    exportClone?.exportHost.remove()
  }
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
let pageBreakFrame: number | null = null

function schedulePreviewScaleUpdate() {
  if (previewScaleFrame !== null) return
  previewScaleFrame = requestAnimationFrame(() => {
    previewScaleFrame = null
    updatePreviewScale()
  })
}

function schedulePageBreakUpdate() {
  if (pageBreakFrame !== null) return
  pageBreakFrame = requestAnimationFrame(() => {
    pageBreakFrame = null
    updatePageBreaks()
  })
}

onMounted(() => {
  nextTick(() => {
    updatePreviewScale()
    schedulePageBreakUpdate()
  })
  if (resumeRef.value) {
    resizeObserver = new ResizeObserver(() => schedulePageBreakUpdate())
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
      schedulePageBreakUpdate()
    })
  }
)

onUnmounted(() => {
  resizeObserver?.disconnect()
  previewResizeObserver?.disconnect()
  if (previewScaleFrame !== null) cancelAnimationFrame(previewScaleFrame)
  if (pageBreakFrame !== null) cancelAnimationFrame(pageBreakFrame)
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

function normalizeForeignObjectCanvasOrigin(
  sourceCanvas: HTMLCanvasElement,
  exportScale: number,
  contentWidth: number,
  contentHeight: number,
  backgroundColor: string,
): HTMLCanvasElement {
  const normalizedCanvas = document.createElement('canvas')
  normalizedCanvas.width = Math.max(1, Math.floor(contentWidth * exportScale))
  normalizedCanvas.height = Math.max(1, Math.floor(contentHeight * exportScale))
  const normalizedContext = normalizedCanvas.getContext('2d')
  if (!normalizedContext) throw new Error('PDF 原点校准画布创建失败')

  normalizedContext.fillStyle = backgroundColor || '#ffffff'
  normalizedContext.fillRect(0, 0, normalizedCanvas.width, normalizedCanvas.height)
  // html2canvas-pro 2.4.0 的 foreignObject 兼容渲染会把原点设为 scale，画布偏移量为 scale² 像素。
  const sourceOriginOffset = exportScale * exportScale
  normalizedContext.drawImage(
    sourceCanvas,
    sourceOriginOffset,
    sourceOriginOffset,
    normalizedCanvas.width,
    normalizedCanvas.height,
    0,
    0,
    normalizedCanvas.width,
    normalizedCanvas.height,
  )
  sourceCanvas.width = 1
  sourceCanvas.height = 1
  return normalizedCanvas
}

function assertCanvasReadable(canvas: HTMLCanvasElement) {
  const sampleCanvas = document.createElement('canvas')
  sampleCanvas.width = 32
  sampleCanvas.height = 32
  const sampleContext = sampleCanvas.getContext('2d', { willReadFrequently: true })
  if (!sampleContext) throw new Error('PDF 画布上下文创建失败')

  sampleContext.drawImage(canvas, 0, 0, sampleCanvas.width, sampleCanvas.height)
  const pixels = sampleContext.getImageData(0, 0, sampleCanvas.width, sampleCanvas.height).data
  let minimumChannel = 255
  let maximumChannel = 0
  for (let index = 0; index < pixels.length; index += 4) {
    minimumChannel = Math.min(minimumChannel, pixels[index] ?? 255, pixels[index + 1] ?? 255, pixels[index + 2] ?? 255)
    maximumChannel = Math.max(maximumChannel, pixels[index] ?? 0, pixels[index + 1] ?? 0, pixels[index + 2] ?? 0)
  }
  if (maximumChannel - minimumChannel < 2) throw new Error('浏览器原生 PDF 画布内容为空')
}

async function exportPDF(mode: ExportQualityMode) {
  if (!resumeRef.value) return
  exporting.value = true
  exportMenuOpen.value = false
  exportProgress.value = 0
  exportProgressText.value = '准备导出...'
  const isHdMode = mode === 'hd'
  const sourceNode = resumeRef.value
  const resumePaperBackground = window
    .getComputedStyle(document.documentElement)
    .getPropertyValue('--resume-paper-background')
    .trim()
  let exportClone: ResumeExportClone | null = null

  try {
    await setExportProgress(8, '准备导出资源...')
    await document.fonts?.ready
    await setExportProgress(18, '加载导出引擎...')
    const [{ default: html2canvasPro }, { jsPDF }] = await Promise.all([
      import('html2canvas-pro'),
      import('jspdf'),
    ])
    await setExportProgress(36, '正在渲染简历画布...')
    const exportScale = isHdMode ? Math.min(4, Math.max(3, window.devicePixelRatio || 1)) : 2
    const renderCanvas = async (exportNode: HTMLElement, renderMode: PdfRenderMode) => {
      const usesForeignObjectRenderer = renderMode === 'foreign-object'
      const contentHeight = Math.ceil(exportNode.getBoundingClientRect().height)
      // foreignObject 兼容渲染先扩展边界，确保校正原点时不会丢失右侧和底部内容。
      const foreignObjectRenderPadding = usesForeignObjectRenderer ? exportScale + 1 : 0
      const sourceCanvas = await html2canvasPro(exportNode, {
        scale: exportScale,
        useCORS: true,
        foreignObjectRendering: usesForeignObjectRenderer,
        width: A4_WIDTH + foreignObjectRenderPadding,
        ...(usesForeignObjectRenderer ? { height: contentHeight + foreignObjectRenderPadding } : {}),
        windowWidth: A4_WIDTH,
        backgroundColor: resumePaperBackground,
        scrollX: 0,
        scrollY: 0,
      })
      return usesForeignObjectRenderer
        ? normalizeForeignObjectCanvasOrigin(
            sourceCanvas,
            exportScale,
            A4_WIDTH,
            contentHeight,
            resumePaperBackground,
          )
        : sourceCanvas
    }

    let activeRenderMode = pdfRenderMode
    let canvas: HTMLCanvasElement | null = null
    while (!canvas) {
      exportClone = createResumeExportClone(sourceNode, activeRenderMode)
      try {
        const renderedCanvas = await renderCanvas(exportClone.exportNode, activeRenderMode)
        assertCanvasReadable(renderedCanvas)
        canvas = renderedCanvas
      } catch (renderError) {
        const fallbackRenderMode = PDF_RENDER_MODE_FALLBACKS[activeRenderMode]
        if (!fallbackRenderMode) throw renderError

        console.warn(
          `PDF ${PDF_RENDER_MODE_LABELS[activeRenderMode]}渲染失败，已切换${PDF_RENDER_MODE_LABELS[fallbackRenderMode]}模式。`,
          renderError,
        )
        exportClone.exportHost.remove()
        exportClone = null
        pdfRenderMode = fallbackRenderMode
        activeRenderMode = fallbackRenderMode
        schedulePageBreakUpdate()
      }
    }
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
    exportClone?.exportHost.remove()
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

<style scoped src="./PreviewPanel.css"></style>
