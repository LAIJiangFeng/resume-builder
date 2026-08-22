<!-- author: jf -->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  Check,
  ChevronDown,
  Clock3,
  CloudUpload,
  Copy,
  FilePlus2,
  FileText,
  PencilLine,
  Search,
  Trash2,
  Upload,
  X,
} from 'lucide-vue-next'
import { useResumeStore } from '@/stores/resume'

type NameDialogMode = 'create' | 'rename'

const search = defineModel<string>('search', { default: '' })
const store = useResumeStore()
const jsonImportInputRef = ref<HTMLInputElement | null>(null)
const nameInputRef = ref<HTMLInputElement | null>(null)
const resumePickerRef = ref<HTMLElement | null>(null)
const resumeSelectorOpen = ref(false)
const nameDialogMode = ref<NameDialogMode | null>(null)
const nameDraft = ref('')
const dialogError = ref('')
const operationError = ref('')
const successMessage = ref('')
const nowTick = ref(Date.now())
let successTimer: ReturnType<typeof setTimeout> | null = null
let autoSaveTicker: ReturnType<typeof setInterval> | null = null
let previousActiveElement: HTMLElement | null = null

const isAutoSavePending = computed(() => store.nextAutoSaveAt !== null)
const currentResumeLabel = computed(() => (
  store.resumeList.find((resume) => resume.resumeId === store.currentResumeId)?.name
  ?? store.currentResumeName
))
const nameDialogTitle = computed(() => (nameDialogMode.value === 'create' ? '新建简历' : '重命名简历'))
const nameDialogDescription = computed(() => (
  nameDialogMode.value === 'create'
    ? '创建后会自动切换到这份新简历。'
    : '修改后的名称会同步保存到云端。'
))
const safeNameDraft = computed(() => nameDraft.value.trim())
const canSubmitName = computed(() => {
  if (!safeNameDraft.value || store.isManaging) return false
  return nameDialogMode.value !== 'rename' || safeNameDraft.value !== store.currentResumeName
})
const autoSaveChipText = computed(() => {
  if (store.isSaving) return '自动保存中...'

  const nextAt = store.nextAutoSaveAt
  if (nextAt) {
    const remainMs = Math.max(nextAt - nowTick.value, 0)
    return `${Math.max(remainMs / 1000, 0.1).toFixed(1)}秒后自动保存`
  }

  const savedAt = store.lastSavedAt
  if (!savedAt) return `自动保存间隔 ${Math.max(store.autoSaveDelayMs / 1000, 0.1).toFixed(1)}秒`

  const elapsedMs = Math.max(nowTick.value - savedAt, 0)
  const label = store.lastSaveMode === 'manual' ? '手动保存' : '自动保存'
  if (elapsedMs < 2_000) return `刚刚${label}`
  if (elapsedMs < 60_000) return `${Math.floor(elapsedMs / 1000)}秒前${label}`
  return `${Math.floor(elapsedMs / 60_000)}分钟前${label}`
})

function clearSuccessTimer() {
  if (!successTimer) return
  clearTimeout(successTimer)
  successTimer = null
}

function showSuccess(message: string) {
  clearSuccessTimer()
  successMessage.value = message
  successTimer = setTimeout(() => {
    successMessage.value = ''
    successTimer = null
  }, 1800)
}

function resetOperationFeedback() {
  operationError.value = ''
  successMessage.value = ''
  clearSuccessTimer()
}

async function handleSave() {
  resetOperationFeedback()
  try {
    await store.saveToStorage()
    showSuccess('已保存到云端')
  } catch (error) {
    operationError.value = error instanceof Error ? error.message : '保存失败'
  }
}

function triggerJsonImport() {
  jsonImportInputRef.value?.click()
}

async function handleImportJson(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  const raw = await file.text()
  input.value = ''
  resetOperationFeedback()
  try {
    await store.importResumeData(raw)
    showSuccess('JSON 已导入')
  } catch (error) {
    operationError.value = error instanceof Error ? error.message : '导入失败'
  }
}

function toggleResumeSelector() {
  if (store.isLoading || store.isManaging) return
  resumeSelectorOpen.value = !resumeSelectorOpen.value
}

function closeResumeSelector() {
  resumeSelectorOpen.value = false
}

async function handleResumeSelect(resumeId: string) {
  closeResumeSelector()
  if (!resumeId || resumeId === store.currentResumeId) return
  resetOperationFeedback()
  try {
    await store.switchResume(resumeId)
  } catch (error) {
    operationError.value = error instanceof Error ? error.message : '切换失败'
  }
}

async function openNameDialog(mode: NameDialogMode) {
  closeResumeSelector()
  resetOperationFeedback()
  dialogError.value = ''
  nameDialogMode.value = mode
  nameDraft.value = mode === 'rename' ? store.currentResumeName : '新简历'
  previousActiveElement = document.activeElement instanceof HTMLElement ? document.activeElement : null
  await nextTick()
  nameInputRef.value?.focus()
  nameInputRef.value?.select()
}

function closeNameDialog() {
  if (store.isManaging) return
  nameDialogMode.value = null
  dialogError.value = ''
  if (previousActiveElement?.isConnected) previousActiveElement.focus()
  previousActiveElement = null
}

async function submitResumeName() {
  const mode = nameDialogMode.value
  const name = safeNameDraft.value
  if (!mode || !name || !canSubmitName.value) return

  dialogError.value = ''
  try {
    if (mode === 'create') {
      await store.createResume(name)
      showSuccess('已新建简历')
    } else {
      await store.renameCurrentResume(name)
      showSuccess('名称已更新')
    }
    nameDialogMode.value = null
    if (previousActiveElement?.isConnected) previousActiveElement.focus()
    previousActiveElement = null
  } catch (error) {
    dialogError.value = error instanceof Error ? error.message : mode === 'create' ? '创建失败' : '重命名失败'
  }
}

async function handleDuplicateResume() {
  resetOperationFeedback()
  try {
    await store.duplicateCurrentResume()
    showSuccess('已复制并切换到副本')
  } catch (error) {
    operationError.value = error instanceof Error ? error.message : '复制失败'
  }
}

async function handleDeleteResume() {
  if (store.resumeList.length <= 1) {
    operationError.value = '至少需要保留一份简历'
    return
  }
  if (!window.confirm(`确定删除“${store.currentResumeName}”吗？`)) return

  resetOperationFeedback()
  try {
    await store.deleteCurrentResume()
    showSuccess('简历已删除')
  } catch (error) {
    operationError.value = error instanceof Error ? error.message : '删除失败'
  }
}

function handleWindowKeydown(event: KeyboardEvent) {
  if (event.key !== 'Escape') return
  if (!nameDialogMode.value && !resumeSelectorOpen.value) return
  event.preventDefault()
  if (nameDialogMode.value) closeNameDialog()
  else closeResumeSelector()
}

function handleDocumentPointerDown(event: MouseEvent) {
  const target = event.target
  if (!(target instanceof Node) || resumePickerRef.value?.contains(target)) return
  closeResumeSelector()
}

onMounted(() => {
  autoSaveTicker = setInterval(() => {
    nowTick.value = Date.now()
  }, 200)
  window.addEventListener('keydown', handleWindowKeydown)
  document.addEventListener('mousedown', handleDocumentPointerDown)
})

onBeforeUnmount(() => {
  if (autoSaveTicker) clearInterval(autoSaveTicker)
  clearSuccessTimer()
  window.removeEventListener('keydown', handleWindowKeydown)
  document.removeEventListener('mousedown', handleDocumentPointerDown)
})
</script>

<template>
  <header class="resume-toolbar" aria-label="简历编辑工具栏">
    <input
      ref="jsonImportInputRef"
      type="file"
      accept=".json,application/json"
      class="visually-hidden-file"
      @change="handleImportJson"
    />

    <div class="resume-toolbar-main">
      <div
        ref="resumePickerRef"
        class="resume-picker"
        :class="{ open: resumeSelectorOpen }"
      >
        <span class="resume-picker-icon" aria-hidden="true">
          <FileText :size="20" stroke-width="1.8" />
        </span>
        <div class="resume-picker-content">
          <span id="resume-library-label" class="resume-picker-label">当前简历</span>
          <button
            id="resume-library-select"
            class="resume-selector-trigger"
            type="button"
            aria-haspopup="listbox"
            aria-labelledby="resume-library-label resume-library-select"
            :aria-expanded="resumeSelectorOpen"
            aria-controls="resume-library-options"
            :disabled="store.isLoading || store.isManaging"
            @click="toggleResumeSelector"
            @keydown.down.prevent="resumeSelectorOpen = true"
          >
            <span>{{ currentResumeLabel }}</span>
            <ChevronDown
              :size="17"
              stroke-width="2"
              aria-hidden="true"
              :class="{ rotated: resumeSelectorOpen }"
            />
          </button>
        </div>

        <Transition name="resume-options">
          <div
            v-if="resumeSelectorOpen"
            id="resume-library-options"
            class="resume-options"
            role="listbox"
            aria-labelledby="resume-library-label"
          >
            <button
              v-for="resume in store.resumeList"
              :key="resume.resumeId"
              type="button"
              role="option"
              :aria-selected="resume.resumeId === store.currentResumeId"
              :class="{ selected: resume.resumeId === store.currentResumeId }"
              @click="handleResumeSelect(resume.resumeId)"
            >
              <span class="resume-option-icon" aria-hidden="true">
                <FileText :size="16" stroke-width="1.8" />
              </span>
              <span class="resume-option-name">{{ resume.name }}</span>
              <Check
                v-if="resume.resumeId === store.currentResumeId"
                :size="17"
                stroke-width="2.2"
                aria-hidden="true"
              />
            </button>
          </div>
        </Transition>
      </div>

      <div class="resume-management-actions" aria-label="简历管理">
        <button
          type="button"
          aria-label="新建简历"
          title="新建简历"
          :disabled="store.isManaging"
          @click="openNameDialog('create')"
        >
          <FilePlus2 :size="18" stroke-width="1.9" aria-hidden="true" />
        </button>
        <button
          type="button"
          aria-label="重命名简历"
          title="重命名简历"
          :disabled="store.isManaging || !store.currentResumeId"
          @click="openNameDialog('rename')"
        >
          <PencilLine :size="18" stroke-width="1.9" aria-hidden="true" />
        </button>
        <button
          type="button"
          aria-label="复制简历"
          title="复制简历"
          :disabled="store.isManaging || !store.currentResumeId"
          @click="handleDuplicateResume"
        >
          <Copy :size="18" stroke-width="1.9" aria-hidden="true" />
        </button>
        <button
          class="danger"
          type="button"
          aria-label="删除简历"
          title="删除简历"
          :disabled="store.isManaging || store.resumeList.length <= 1"
          @click="handleDeleteResume"
        >
          <Trash2 :size="18" stroke-width="1.9" aria-hidden="true" />
        </button>
      </div>
    </div>

    <div class="resume-toolbar-utility-row">
      <label class="toolbar-search" aria-label="搜索简历模块">
        <Search :size="18" stroke-width="1.8" aria-hidden="true" />
        <input v-model="search" placeholder="搜索模块" />
        <span class="search-shortcut" aria-hidden="true">模块筛选</span>
      </label>
      <div class="editor-header-actions">
        <span
          class="save-status"
          :class="{ pending: isAutoSavePending, saving: store.isSaving }"
          :title="autoSaveChipText"
          :aria-label="autoSaveChipText"
          role="status"
          aria-live="polite"
        >
          <span v-if="store.isSaving" class="save-status-loading" aria-hidden="true"></span>
          <Clock3 v-else :size="17" stroke-width="1.9" aria-hidden="true" />
        </span>
        <button
          class="toolbar-action secondary"
          type="button"
          aria-label="导入 JSON"
          title="导入 JSON"
          @click="triggerJsonImport"
        >
          <Upload :size="17" stroke-width="1.9" aria-hidden="true" />
          <span>导入 JSON</span>
        </button>
        <button
          class="toolbar-action primary"
          type="button"
          aria-label="保存云端"
          title="保存云端"
          :disabled="store.isSaving || store.isLoading"
          @click="handleSave"
        >
          <CloudUpload :size="17" stroke-width="1.9" aria-hidden="true" />
          <span>保存云端</span>
        </button>
      </div>
    </div>

    <Transition name="toolbar-feedback">
      <p v-if="successMessage" class="toolbar-feedback success" role="status">
        <Check :size="15" stroke-width="2.1" aria-hidden="true" />
        {{ successMessage }}
      </p>
    </Transition>
    <p v-if="operationError || store.saveError" class="toolbar-feedback error" role="alert">
      {{ operationError || store.saveError }}
    </p>
  </header>

  <Teleport to="body">
    <Transition name="resume-name-dialog">
      <div v-if="nameDialogMode" class="resume-name-dialog-layer" @click.self="closeNameDialog">
        <form class="resume-name-dialog" role="dialog" aria-modal="true" @submit.prevent="submitResumeName">
          <header>
            <span class="resume-name-dialog-icon" aria-hidden="true">
              <FilePlus2 v-if="nameDialogMode === 'create'" :size="21" stroke-width="1.8" />
              <PencilLine v-else :size="21" stroke-width="1.8" />
            </span>
            <div>
              <h2>{{ nameDialogTitle }}</h2>
              <p>{{ nameDialogDescription }}</p>
            </div>
            <button type="button" aria-label="关闭" :disabled="store.isManaging" @click="closeNameDialog">
              <X :size="19" stroke-width="1.9" aria-hidden="true" />
            </button>
          </header>

          <label for="resume-name-input">简历名称</label>
          <input
            id="resume-name-input"
            ref="nameInputRef"
            v-model="nameDraft"
            maxlength="80"
            autocomplete="off"
            placeholder="请输入简历名称"
            :disabled="store.isManaging"
            @input="dialogError = ''"
          />
          <div class="resume-name-meta">
            <span>{{ dialogError }}</span>
            <span>{{ nameDraft.length }}/80</span>
          </div>

          <footer>
            <button type="button" class="dialog-cancel" :disabled="store.isManaging" @click="closeNameDialog">
              取消
            </button>
            <button type="submit" class="dialog-confirm" :disabled="!canSubmitName">
              {{ store.isManaging ? '处理中...' : nameDialogMode === 'create' ? '创建简历' : '保存名称' }}
            </button>
          </footer>
        </form>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.resume-toolbar {
  position: relative;
  z-index: 30;
  container-type: inline-size;
  margin-bottom: 14px;
  padding: 12px;
  border: 1px solid var(--border-soft);
  border-radius: 18px;
  background: linear-gradient(
    135deg,
    var(--surface-soft),
    color-mix(in srgb, var(--surface-base) 88%, var(--primary-50))
  );
}

.visually-hidden-file {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  clip-path: inset(50%);
  white-space: nowrap;
}

.resume-toolbar-main {
  display: grid;
  grid-template-columns: minmax(250px, 1fr) auto;
  align-items: center;
  gap: 10px;
}

.resume-toolbar-utility-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}

.resume-picker {
  position: relative;
  min-width: 0;
  height: 52px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  background: var(--surface-base);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.resume-picker:focus-within {
  border-color: var(--primary-400);
  box-shadow: 0 0 0 4px var(--theme-focus-ring);
}

.resume-picker.open {
  border-color: var(--primary-400);
  box-shadow: 0 0 0 4px var(--theme-focus-ring);
}

.resume-picker-icon {
  width: 34px;
  height: 34px;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 11px;
  background: var(--primary-50);
  color: var(--primary-500);
}

.resume-picker-content {
  min-width: 0;
  flex: 1;
  display: grid;
  gap: 1px;
}

.resume-picker-label {
  color: var(--text-tertiary);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  line-height: 1.2;
}

.resume-management-actions {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px;
  border: 1px solid var(--border-soft);
  border-radius: 14px;
  background: var(--surface-base);
  box-shadow: var(--shadow-sm);
}

.resume-management-actions button,
.save-status {
  width: 38px;
  height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 11px;
  background: transparent;
  color: var(--text-secondary);
}

.resume-management-actions button {
  cursor: pointer;
  transition: background-color 0.18s ease, color 0.18s ease, transform 0.18s ease;
}

.resume-management-actions button:hover:not(:disabled) {
  background: var(--primary-50);
  color: var(--primary-500);
  transform: translateY(-1px);
}

.resume-management-actions button.danger:hover:not(:disabled) {
  background: var(--surface-danger);
  color: var(--text-danger);
}

.resume-management-actions button:focus-visible,
.toolbar-action:focus-visible,
.resume-name-dialog button:focus-visible {
  outline: 3px solid var(--theme-focus-ring);
  outline-offset: 2px;
}

.resume-management-actions button:disabled,
.resume-selector-trigger:disabled,
.toolbar-action:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.editor-header-actions {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 7px;
}

.save-status {
  position: relative;
  overflow: hidden;
  flex: 0 0 auto;
  background: var(--primary-50);
  color: var(--primary-500);
}

.save-status.pending {
  animation: save-status-breathe 1.1s ease-in-out infinite;
}

.save-status.saving {
  background: var(--surface-success);
  color: var(--text-success);
}

.save-status-loading {
  width: 15px;
  height: 15px;
  border: 2px solid color-mix(in srgb, var(--text-success) 24%, transparent);
  border-top-color: var(--text-success);
  border-radius: 50%;
  animation: save-status-spin 0.75s linear infinite;
}

.toolbar-action {
  min-height: 38px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 0 13px;
  border-radius: 12px;
  font: inherit;
  font-size: 12px;
  font-weight: 750;
  white-space: nowrap;
  cursor: pointer;
  transition: border-color 0.18s ease, background-color 0.18s ease, color 0.18s ease;
}

.toolbar-action.secondary {
  border: 1px solid var(--border-color);
  background: var(--surface-base);
  color: var(--text-primary);
}

.toolbar-action.secondary:hover:not(:disabled) {
  border-color: var(--primary-300);
  color: var(--primary-500);
}

.toolbar-action.primary {
  border: 1px solid var(--primary-500);
  background: var(--primary-500);
  color: var(--text-inverse);
  box-shadow: var(--shadow-brand);
}

.toolbar-action.primary:hover:not(:disabled) {
  background: var(--primary-600);
}

.toolbar-search {
  width: 100%;
  height: 42px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  border: 1px solid var(--border-color);
  border-radius: 13px;
  background: var(--surface-base);
  color: var(--text-secondary);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.toolbar-search:focus-within {
  border-color: var(--primary-400);
  box-shadow: 0 0 0 4px var(--theme-focus-ring);
}

.toolbar-search input {
  min-width: 0;
  flex: 1;
  height: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text-primary);
  font: inherit;
  font-size: 13px;
}

.toolbar-search input::placeholder {
  color: var(--text-tertiary);
}

.search-shortcut {
  flex: 0 0 auto;
  padding: 4px 7px;
  border-radius: 7px;
  background: var(--surface-muted);
  color: var(--text-tertiary);
  font-size: 10px;
  font-weight: 700;
}

.toolbar-feedback {
  display: flex;
  align-items: center;
  gap: 5px;
  margin: 8px 2px 0;
  font-size: 12px;
  font-weight: 700;
}

.toolbar-feedback.success {
  color: var(--text-success);
}

.toolbar-feedback.error {
  color: var(--text-danger);
}

.resume-name-dialog-layer {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: grid;
  place-items: center;
  padding: 20px;
  background: var(--overlay-backdrop);
  backdrop-filter: blur(5px);
}

.resume-name-dialog {
  width: min(420px, 100%);
  padding: 20px;
  border: 1px solid var(--border-soft);
  border-radius: 20px;
  background: var(--surface-glass-strong);
  box-shadow: var(--shadow-dialog);
}

.resume-name-dialog header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: start;
  gap: 11px;
}

.resume-name-dialog-icon {
  width: 40px;
  height: 40px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 13px;
  background: var(--primary-50);
  color: var(--primary-500);
}

.resume-name-dialog h2 {
  margin: 1px 0 0;
  color: var(--text-primary);
  font-size: 18px;
  line-height: 1.25;
}

.resume-name-dialog header p {
  margin: 4px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.45;
}

.resume-name-dialog header button {
  width: 34px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 0;
  border-radius: 10px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
}

.resume-name-dialog > label {
  display: block;
  margin-top: 20px;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
}

.resume-name-dialog > input {
  width: 100%;
  height: 46px;
  margin-top: 7px;
  padding: 0 13px;
  border: 1px solid var(--border-color);
  border-radius: 12px;
  outline: 0;
  background: var(--surface-base);
  color: var(--text-primary);
  font: inherit;
  font-size: 14px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.resume-name-dialog > input:focus {
  border-color: var(--primary-400);
  box-shadow: 0 0 0 4px var(--theme-focus-ring);
}

.resume-name-meta {
  min-height: 18px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 5px;
  color: var(--text-tertiary);
  font-size: 11px;
}

.resume-name-meta span:first-child {
  color: var(--text-danger);
}

.resume-name-dialog footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
}

.resume-name-dialog footer button {
  min-height: 38px;
  padding: 0 15px;
  border-radius: 11px;
  font: inherit;
  font-size: 12px;
  font-weight: 750;
  cursor: pointer;
}

.resume-name-dialog footer button:disabled {
  cursor: not-allowed;
  opacity: 0.48;
}

.dialog-cancel {
  border: 1px solid var(--border-color);
  background: var(--surface-base);
  color: var(--text-secondary);
}

.dialog-confirm {
  border: 1px solid var(--primary-500);
  background: var(--primary-500);
  color: var(--text-inverse);
}

.toolbar-feedback-enter-active,
.toolbar-feedback-leave-active,
.resume-name-dialog-enter-active,
.resume-name-dialog-leave-active {
  transition: opacity 0.18s ease;
}

.toolbar-feedback-enter-from,
.toolbar-feedback-leave-to,
.resume-name-dialog-enter-from,
.resume-name-dialog-leave-to {
  opacity: 0;
}

.resume-name-dialog-enter-active .resume-name-dialog,
.resume-name-dialog-leave-active .resume-name-dialog {
  transition: transform 0.2s ease;
}

.resume-name-dialog-enter-from .resume-name-dialog,
.resume-name-dialog-leave-to .resume-name-dialog {
  transform: translateY(10px) scale(0.98);
}

@keyframes save-status-spin {
  to { transform: rotate(360deg); }
}

@keyframes save-status-breathe {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.62; }
}

@container (max-width: 520px) {
  .resume-toolbar {
    padding: 9px;
  }

  .resume-toolbar-main {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
  }

  .resume-picker {
    height: 46px;
    gap: 8px;
    padding: 5px 8px;
  }

  .resume-picker-icon {
    width: 32px;
    height: 32px;
    border-radius: 10px;
  }

  .resume-management-actions {
    justify-self: end;
    gap: 3px;
    padding: 4px;
    border-radius: 12px;
  }

  .resume-management-actions button {
    width: 34px;
    height: 34px;
    border-radius: 9px;
  }

  .resume-toolbar-utility-row {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 8px;
    margin-top: 8px;
  }

  .editor-header-actions {
    width: auto;
    gap: 5px;
  }

  .toolbar-search {
    height: 38px;
    gap: 7px;
    padding: 0 10px;
  }

  .toolbar-action {
    min-height: 38px;
    flex: 0 0 auto;
    gap: 5px;
    padding: 0 9px;
    border-radius: 10px;
    font-size: 11px;
  }

  .save-status,
  .search-shortcut {
    display: none;
  }
}

@container (max-width: 440px) {
  .resume-toolbar {
    padding: 8px;
  }

  .resume-management-actions {
    gap: 2px;
    padding: 3px;
  }

  .resume-management-actions button {
    width: 32px;
    height: 32px;
  }

  .toolbar-action {
    width: 36px;
    padding: 0;
  }

  .toolbar-action span {
    display: none;
  }
}

@container (max-width: 300px) {
  .resume-picker-icon {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .save-status.pending,
  .save-status-loading,
  .resume-options-enter-active,
  .resume-options-leave-active {
    animation: none;
    transition: none;
  }

  .resume-management-actions button,
  .toolbar-action,
  .resume-name-dialog-enter-active .resume-name-dialog,
  .resume-name-dialog-leave-active .resume-name-dialog {
    transition: none;
  }
}
</style>
<style scoped src="./ResumeToolbar.selector.css"></style>
