<script setup lang="ts">
// author: jf
import { computed, onUnmounted, reactive, ref, type Component } from 'vue'
import { useResumeStore } from '@/stores/resume'
import ResumeToolbar from './ResumeToolbar.vue'
import BasicInfoEditor from './editors/BasicInfoEditor.vue'
import EducationEditor from './editors/EducationEditor.vue'
import SkillsEditor from './editors/SkillsEditor.vue'
import WorkExperienceEditor from './editors/WorkExperienceEditor.vue'
import ProjectExperienceEditor from './editors/ProjectExperienceEditor.vue'
import AwardsEditor from './editors/AwardsEditor.vue'
import SelfIntroEditor from './editors/SelfIntroEditor.vue'
import AiOptimizePanel from '@/components/ai/AiOptimizePanel.vue'
import { getModuleIconPaths, MODULE_ICON_VIEWBOX } from '@/constants/moduleIcons'

const props = withDefaults(
  defineProps<{
    moduleSidebarCollapsed?: boolean
  }>(),
  {
    moduleSidebarCollapsed: false,
  }
)

const emit = defineEmits<{
  (e: 'toggle-module-sidebar'): void
}>()

const store = useResumeStore()
const searchValue = ref('')
const showAiPanel = ref(false)
const mobileModuleDrawerOpen = ref(false)
const moduleNavListRef = ref<HTMLElement | null>(null)
const draggingModuleKey = ref<string | null>(null)
const dragOverModuleKey = ref<string | null>(null)
let activeSortPointerId: number | null = null
let activeSortPointerTarget: HTMLElement | null = null
let activeSortStartX = 0
let activeSortStartY = 0
let activeSortMoved = false
let activeSortMouse = false
let sortPointerListenersBound = false
let sortMouseListenersBound = false

function handleAiClick() {
  showAiPanel.value = true
}

const expanded = reactive<Record<string, boolean>>({
  basicInfo: true,
  education: false,
  skills: false,
  workExperience: false,
  projectExperience: false,
  awards: false,
  selfIntro: false,
})

const editorMap: Record<string, Component> = {
  basicInfo: BasicInfoEditor,
  education: EducationEditor,
  skills: SkillsEditor,
  workExperience: WorkExperienceEditor,
  projectExperience: ProjectExperienceEditor,
  awards: AwardsEditor,
  selfIntro: SelfIntroEditor,
}

const visibleCount = computed(() => store.modules.filter((m) => m.visible).length)
const searchKeyword = computed(() => searchValue.value.trim())
const filteredModules = computed(() =>
  store.modules.filter((m) => (searchKeyword.value ? m.label.includes(searchKeyword.value) : true))
)

function hasTextContent(value: string | undefined): boolean {
  if (!value) return false
  const text = value
    .replace(/<[^>]*>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .trim()
  return text.length > 0
}

function countFilled(values: Array<string | undefined>): number {
  return values.reduce((count, value) => count + (value?.trim() ? 1 : 0), 0)
}

function scoreByFilled(values: Array<string | undefined>): number {
  if (values.length === 0) return 0
  return countFilled(values) / values.length
}

const moduleCompletion = computed<Record<string, number>>(() => {
  const basic = store.basicInfo

  const basicInfoScore = scoreByFilled([
    basic.name,
    basic.phone,
    basic.email,
    basic.jobTitle,
    basic.expectedLocation,
    basic.educationLevel,
  ])

  const firstEducation = store.educationList.find((e) =>
    [e.school, e.major, e.degree, e.startDate].some((value) => value?.trim())
  )
  const educationScore = firstEducation
    ? scoreByFilled([firstEducation.school, firstEducation.major, firstEducation.degree, firstEducation.startDate])
    : 0

  const firstWork = store.workList.find((w) =>
    [w.company, w.position, w.startDate, w.description].some((value) => value?.trim())
  )
  const workScore = firstWork
    ? scoreByFilled([firstWork.company, firstWork.position, firstWork.startDate, firstWork.description])
    : 0

  const firstProject = store.projectList.find((p) =>
    [p.name, p.role, p.startDate, p.mainWork].some((value) => value?.trim())
  )
  const projectScore = firstProject
    ? scoreByFilled([firstProject.name, firstProject.role, firstProject.startDate, firstProject.mainWork])
    : 0

  const firstAward = store.awardList.find((a) => [a.name, a.date].some((value) => value?.trim()))
  const awardsScore = firstAward ? scoreByFilled([firstAward.name, firstAward.date]) : 0

  return {
    basicInfo: basicInfoScore,
    education: educationScore,
    skills: hasTextContent(store.skills) ? 1 : 0,
    workExperience: workScore,
    projectExperience: projectScore,
    awards: awardsScore,
    selfIntro: hasTextContent(store.selfIntro) ? 1 : 0,
  }
})

const completionPercent = computed(() => {
  const enabledModules = store.modules.filter((m) => m.visible)
  if (enabledModules.length === 0) return 0
  const total = enabledModules.reduce((sum, mod) => sum + (moduleCompletion.value[mod.key] ?? 0), 0)
  return Math.round((total / enabledModules.length) * 100)
})

const isDefaultOrder = computed(() => store.isDefaultModuleOrder())

function handleResetOrder() {
  store.resetModuleOrder()
}

function toggleExpand(key: string) {
  expanded[key] = !expanded[key]
}

function handleModuleNavClick(key: string) {
  toggleExpand(key)
}

function moduleIconPaths(key: string): string[] {
  return getModuleIconPaths(key)
}

function handleSwitchDragStart(event: DragEvent, key: string) {
  if (activeSortPointerId !== null) {
    event.preventDefault()
    return
  }
  if (key === 'basicInfo') {
    event.preventDefault()
    return
  }
  draggingModuleKey.value = key
  event.dataTransfer?.setData('text/plain', key)
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

function handleSwitchDragOver(event: DragEvent, key: string) {
  if (!draggingModuleKey.value || draggingModuleKey.value === key) return
  event.preventDefault()
  dragOverModuleKey.value = key
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

function handleSwitchDrop(targetKey: string) {
  const sourceKey = draggingModuleKey.value
  if (!sourceKey || sourceKey === targetKey) return
  store.reorderModule(sourceKey, targetKey)
  dragOverModuleKey.value = null
}

function clearSwitchDragState() {
  releaseSortPointer()
  unbindSortPointerListeners()
  unbindSortMouseListeners()
  activeSortPointerId = null
  activeSortPointerTarget = null
  activeSortStartX = 0
  activeSortStartY = 0
  activeSortMoved = false
  activeSortMouse = false
  draggingModuleKey.value = null
  dragOverModuleKey.value = null
}

function handleSwitchDragEnd() {
  clearSwitchDragState()
}

function findPointerTargetModuleKey(clientX: number, clientY: number): string | null {
  const list = moduleNavListRef.value
  if (!list) return null

  const listRect = list.getBoundingClientRect()
  const edgePadding = 16
  if (
    clientX < listRect.left - edgePadding ||
    clientX > listRect.right + edgePadding ||
    clientY < listRect.top - edgePadding ||
    clientY > listRect.bottom + edgePadding
  ) {
    return null
  }

  const items = Array.from(list.querySelectorAll<HTMLElement>('.module-nav-item[data-module-key]'))
  let closestKey: string | null = null
  let closestDistance = Number.POSITIVE_INFINITY

  for (const item of items) {
    const key = item.dataset.moduleKey
    if (!key || key === draggingModuleKey.value) continue

    const rect = item.getBoundingClientRect()
    if (clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom) {
      return key
    }

    const centerX = rect.left + rect.width / 2
    const centerY = rect.top + rect.height / 2
    const distance = Math.hypot(clientX - centerX, clientY - centerY)
    if (distance < closestDistance) {
      closestDistance = distance
      closestKey = key
    }
  }

  return closestKey
}

function captureSortPointer(event: PointerEvent) {
  const target = event.currentTarget
  if (target instanceof HTMLElement) {
    activeSortPointerTarget = target
    target.setPointerCapture(event.pointerId)
  }
}

function releaseSortPointer(event?: PointerEvent) {
  const target = activeSortPointerTarget
  const pointerId = event?.pointerId ?? activeSortPointerId
  if (target instanceof HTMLElement && pointerId !== null && pointerId >= 0 && target.hasPointerCapture(pointerId)) {
    target.releasePointerCapture(pointerId)
  }
  activeSortPointerTarget = null
}

function bindSortPointerListeners() {
  if (sortPointerListenersBound) return
  window.addEventListener('pointermove', handleActiveSwitchPointerMove, true)
  window.addEventListener('pointerup', handleActiveSwitchPointerUp, true)
  window.addEventListener('pointercancel', handleActiveSwitchPointerCancel, true)
  sortPointerListenersBound = true
}

function unbindSortPointerListeners() {
  if (!sortPointerListenersBound) return
  window.removeEventListener('pointermove', handleActiveSwitchPointerMove, true)
  window.removeEventListener('pointerup', handleActiveSwitchPointerUp, true)
  window.removeEventListener('pointercancel', handleActiveSwitchPointerCancel, true)
  sortPointerListenersBound = false
}

function bindSortMouseListeners() {
  if (sortMouseListenersBound) return
  window.addEventListener('mousemove', handleActiveSwitchMouseMove, true)
  window.addEventListener('mouseup', handleActiveSwitchMouseUp, true)
  sortMouseListenersBound = true
}

function unbindSortMouseListeners() {
  if (!sortMouseListenersBound) return
  window.removeEventListener('mousemove', handleActiveSwitchMouseMove, true)
  window.removeEventListener('mouseup', handleActiveSwitchMouseUp, true)
  sortMouseListenersBound = false
}

function updateActiveSwitchDrag(clientX: number, clientY: number) {
  if (Math.hypot(clientX - activeSortStartX, clientY - activeSortStartY) < 8) return

  activeSortMoved = true
  dragOverModuleKey.value = findPointerTargetModuleKey(clientX, clientY)
}

function commitActiveSwitchDrag(clientX: number, clientY: number) {
  const sourceKey = draggingModuleKey.value
  const targetKey = activeSortMoved ? (dragOverModuleKey.value ?? findPointerTargetModuleKey(clientX, clientY)) : null
  if (sourceKey && targetKey && sourceKey !== targetKey) {
    store.reorderModule(sourceKey, targetKey)
  }
}

function handleSwitchPointerDown(event: PointerEvent, key: string) {
  if (key === 'basicInfo' || activeSortPointerId !== null || activeSortMouse) return

  event.preventDefault()
  event.stopPropagation()
  activeSortPointerId = event.pointerId
  activeSortStartX = event.clientX
  activeSortStartY = event.clientY
  activeSortMoved = false
  draggingModuleKey.value = key
  dragOverModuleKey.value = null
  captureSortPointer(event)
  bindSortPointerListeners()
}

function handleActiveSwitchPointerMove(event: PointerEvent) {
  if (activeSortPointerId !== event.pointerId || !draggingModuleKey.value) return

  event.preventDefault()
  event.stopPropagation()
  updateActiveSwitchDrag(event.clientX, event.clientY)
}

function handleActiveSwitchPointerUp(event: PointerEvent) {
  if (activeSortPointerId !== event.pointerId || !draggingModuleKey.value) return

  event.preventDefault()
  event.stopPropagation()
  commitActiveSwitchDrag(event.clientX, event.clientY)
  releaseSortPointer(event)
  clearSwitchDragState()
}

function handleActiveSwitchPointerCancel(event: PointerEvent) {
  if (activeSortPointerId !== event.pointerId || !draggingModuleKey.value) return

  event.preventDefault()
  event.stopPropagation()
  releaseSortPointer(event)
  clearSwitchDragState()
}

function handleSwitchMouseDown(event: MouseEvent, key: string) {
  if (key === 'basicInfo' || activeSortPointerId !== null || activeSortMouse) return

  event.preventDefault()
  event.stopPropagation()
  activeSortMouse = true
  activeSortStartX = event.clientX
  activeSortStartY = event.clientY
  activeSortMoved = false
  draggingModuleKey.value = key
  dragOverModuleKey.value = null
  bindSortMouseListeners()
}

function handleActiveSwitchMouseMove(event: MouseEvent) {
  if (!activeSortMouse || !draggingModuleKey.value) return

  event.preventDefault()
  event.stopPropagation()
  updateActiveSwitchDrag(event.clientX, event.clientY)
}

function handleActiveSwitchMouseUp(event: MouseEvent) {
  if (!activeSortMouse || !draggingModuleKey.value) return

  event.preventDefault()
  event.stopPropagation()
  commitActiveSwitchDrag(event.clientX, event.clientY)
  clearSwitchDragState()
}

onUnmounted(() => {
  clearSwitchDragState()
})
</script>

<template>
  <main class="editor-panel">
    <button
      class="mobile-module-fab"
      type="button"
      aria-controls="resume-module-drawer"
      :aria-expanded="mobileModuleDrawerOpen"
      @click="mobileModuleDrawerOpen = true"
    >
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 6h16" />
        <path d="M4 12h16" />
        <path d="M4 18h16" />
      </svg>
      模块
    </button>

    <div
      v-if="mobileModuleDrawerOpen"
      class="mobile-module-mask"
      aria-hidden="true"
      @click="mobileModuleDrawerOpen = false"
    ></div>

    <div class="editor-workbench">
      <aside
        id="resume-module-drawer"
        class="editor-side-card"
        :class="{
          'mobile-module-drawer-open': mobileModuleDrawerOpen,
          'desktop-module-sidebar-collapsed': props.moduleSidebarCollapsed,
        }"
        aria-label="简历模块与快捷操作"
      >
        <button
          class="desktop-module-collapse"
          type="button"
          :aria-expanded="!props.moduleSidebarCollapsed"
          :aria-label="props.moduleSidebarCollapsed ? '展开模块侧栏' : '收起模块侧栏'"
          :title="props.moduleSidebarCollapsed ? '展开模块侧栏' : '收起模块侧栏'"
          @click="emit('toggle-module-sidebar')"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path :d="props.moduleSidebarCollapsed ? 'm9 6 6 6-6 6' : 'm15 6-6 6 6 6'" />
          </svg>
        </button>

        <button
          class="mobile-module-close"
          type="button"
          aria-label="关闭模块选择"
          @click="mobileModuleDrawerOpen = false"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 6l12 12" />
            <path d="M18 6 6 18" />
          </svg>
        </button>

        <section class="completion-card" aria-label="简历完整度">
          <div class="completion-head">
            <span>简历完整度</span>
            <strong>{{ completionPercent }}%</strong>
          </div>
          <div class="completion-track" aria-hidden="true">
            <span :style="{ width: `${completionPercent}%` }"></span>
          </div>
          <p>{{ visibleCount }} / {{ store.modules.length }} 个模块已启用</p>
        </section>

        <ul ref="moduleNavListRef" class="module-nav-list">
          <li
            v-for="mod in store.modules"
            :key="`nav-${mod.key}`"
            class="module-nav-item"
            :data-module-key="mod.key"
            :data-label="mod.label"
            :class="{
              active: expanded[mod.key] && mod.visible,
              muted: !mod.visible,
              draggable: mod.key !== 'basicInfo',
              dragging: draggingModuleKey === mod.key,
              'drag-over': dragOverModuleKey === mod.key,
            }"
            :draggable="mod.key !== 'basicInfo'"
            @dragstart="handleSwitchDragStart($event, mod.key)"
            @dragover="handleSwitchDragOver($event, mod.key)"
            @drop.prevent="handleSwitchDrop(mod.key)"
            @dragend="handleSwitchDragEnd"
          >
            <button
              type="button"
              class="module-nav-btn"
              @click="handleModuleNavClick(mod.key)"
            >
              <span class="module-nav-icon" aria-hidden="true">
                <svg :viewBox="MODULE_ICON_VIEWBOX">
                  <path v-for="(d, idx) in moduleIconPaths(mod.key)" :key="`nav-${mod.key}-${idx}`" :d="d" />
                </svg>
              </span>
              <span>{{ mod.label }}</span>
            </button>
            <div class="module-nav-actions">
              <span
                v-if="mod.key !== 'basicInfo'"
                class="module-drag-chip"
                title="按住拖拽按钮排序"
                @pointerdown="handleSwitchPointerDown($event, mod.key)"
                @mousedown="handleSwitchMouseDown($event, mod.key)"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M9 5h.01" />
                  <path d="M15 5h.01" />
                  <path d="M9 12h.01" />
                  <path d="M15 12h.01" />
                  <path d="M9 19h.01" />
                  <path d="M15 19h.01" />
                </svg>
                拖拽
              </span>
              <label class="toggle-switch nav-toggle-switch" @click.stop>
                <input
                  type="checkbox"
                  :checked="mod.visible"
                  :aria-label="`${mod.label}开关`"
                  @change.stop="store.toggleModule(mod.key)"
                />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </li>
        </ul>

        <div class="side-actions">
          <button
            class="side-action"
            type="button"
            :disabled="isDefaultOrder"
            @click="handleResetOrder"
          >
            恢复排序
          </button>
          <button class="side-action primary" type="button" @click="handleAiClick">AI 建议</button>
        </div>
      </aside>

      <section class="info-editor">
        <ResumeToolbar v-model:search="searchValue" />

        <div class="module-sections">
          <article
            v-for="mod in filteredModules"
            :key="mod.key"
            class="module-block"
            :class="{ disabled: !mod.visible }"
          >
            <header class="module-head" @click="toggleExpand(mod.key)">
              <div class="module-head-left">
                <span class="module-head-icon" aria-hidden="true">
                  <svg class="module-head-icon-svg" :viewBox="MODULE_ICON_VIEWBOX">
                    <path v-for="(d, idx) in moduleIconPaths(mod.key)" :key="`${mod.key}-${idx}`" :d="d" />
                  </svg>
                </span>
                <span class="module-head-title">{{ mod.label }}</span>
              </div>
              <div class="module-head-right">
                <span v-if="!mod.visible" class="disabled-tag">已关闭</span>
                <span class="expand-text">{{ expanded[mod.key] && mod.visible ? '收起' : '展开' }}</span>
              </div>
            </header>

            <div v-if="expanded[mod.key] && mod.visible" class="module-body">
              <component :is="editorMap[mod.key]" />
            </div>
          </article>

          <div v-if="filteredModules.length === 0" class="empty-result">没有匹配的模块</div>
        </div>
      </section>
    </div>

    <AiOptimizePanel
      :open="showAiPanel"
      @close="showAiPanel = false"
    />
  </main>
</template>

<style scoped src="./EditorPanel.css"></style>
<style scoped src="./EditorPanel.responsive.css"></style>
