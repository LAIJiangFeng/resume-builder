<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
// author: jf

const props = defineProps<{
  modelValue: string
  placeholder?: string
  rows?: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const editorRef = ref<HTMLDivElement | null>(null)
const isFocused = ref(false)
const showPlaceholder = ref(!props.modelValue)
const defaultTextColor = ref('')

// Sync incoming model value → DOM (only when not focused to avoid cursor jumps)
watch(() => props.modelValue, (val) => {
  if (!editorRef.value || isFocused.value) return
  if (editorRef.value.innerHTML !== val) {
    editorRef.value.innerHTML = val || ''
  }
  showPlaceholder.value = !val
})

onMounted(() => {
  defaultTextColor.value = window
    .getComputedStyle(document.documentElement)
    .getPropertyValue('--resume-paper-text')
    .trim()
  if (editorRef.value) {
    editorRef.value.innerHTML = props.modelValue || ''
    showPlaceholder.value = !props.modelValue
  }
})

function onInput() {
  const html = editorRef.value?.innerHTML ?? ''
  // Treat empty div as empty string
  const clean = html === '<br>' || html === '<div><br></div>' ? '' : html
  showPlaceholder.value = !clean
  emit('update:modelValue', clean)
}

function execCmd(cmd: string, value?: string) {
  document.execCommand(cmd, false, value)
  editorRef.value?.focus()
  onInput()
}

function setFontSize(e: Event) {
  const target = e.target as HTMLSelectElement
  const size = target.value
  if (!size) return
  // execCommand fontSize uses 1-7 scale; we use a span approach instead
  document.execCommand('fontSize', false, '7')
  const fontEls = editorRef.value?.querySelectorAll('font[size="7"]')
  fontEls?.forEach(el => {
    const span = document.createElement('span')
    span.style.fontSize = size
    span.innerHTML = el.innerHTML
    el.parentNode?.replaceChild(span, el)
  })
  // Keep list item marker size in sync with content size.
  applyFontSizeToSelectedListItems(size)
  editorRef.value?.focus()
  onInput()
  // Reset select so re-selecting the same size still triggers change next time.
  target.value = ''
}

function applyFontSizeToSelectedListItems(size: string) {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return

  const range = selection.getRangeAt(0)
  const startEl =
    range.startContainer.nodeType === Node.ELEMENT_NODE
      ? (range.startContainer as Element)
      : range.startContainer.parentElement
  const endEl =
    range.endContainer.nodeType === Node.ELEMENT_NODE
      ? (range.endContainer as Element)
      : range.endContainer.parentElement

  const startLi = startEl?.closest('li') as HTMLElement | null
  const endLi = endEl?.closest('li') as HTMLElement | null

  if (startLi && endLi && startLi.parentElement && startLi.parentElement === endLi.parentElement) {
    const siblings = Array.from(startLi.parentElement.children).filter(
      (node) => node instanceof HTMLElement && node.tagName === 'LI'
    ) as HTMLElement[]
    const startIndex = siblings.indexOf(startLi)
    const endIndex = siblings.indexOf(endLi)
    if (startIndex > -1 && endIndex > -1) {
      const from = Math.min(startIndex, endIndex)
      const to = Math.max(startIndex, endIndex)
      for (let i = from; i <= to; i += 1) {
        const li = siblings[i]
        if (li) li.style.fontSize = size
      }
      return
    }
  }

  if (startLi) startLi.style.fontSize = size
  if (endLi && endLi !== startLi) endLi.style.fontSize = size
}

function setColor(e: Event) {
  const color = (e.target as HTMLInputElement).value
  execCmd('foreColor', color)
}

function isActive(cmd: string): boolean {
  try { return document.queryCommandState(cmd) } catch { return false }
}
</script>

<template>
  <div class="rich-editor-wrap" :class="{ focused: isFocused }">
    <!-- Toolbar -->
    <div class="rich-toolbar">
      <button type="button" class="tool-btn" :class="{ active: isActive('bold') }" @mousedown.prevent="execCmd('bold')" title="粗体">
        <strong>B</strong>
      </button>
      <button type="button" class="tool-btn" :class="{ active: isActive('italic') }" @mousedown.prevent="execCmd('italic')" title="斜体">
        <em>I</em>
      </button>
      <button type="button" class="tool-btn" :class="{ active: isActive('underline') }" @mousedown.prevent="execCmd('underline')" title="下划线">
        <u>U</u>
      </button>
      <div class="tool-divider"></div>
      <select class="tool-select" @change="setFontSize" title="字体大小">
        <option value="">字号</option>
        <option value="10px">10</option>
        <option value="11px">11</option>
        <option value="12px">12</option>
        <option value="13px">13</option>
        <option value="14px">14</option>
        <option value="16px">16</option>
        <option value="18px">18</option>
        <option value="20px">20</option>
      </select>
      <input type="color" class="tool-color" :value="defaultTextColor" @change="setColor" title="字体颜色" />
      <div class="tool-divider"></div>
      <button type="button" class="tool-btn" @mousedown.prevent="execCmd('insertUnorderedList')" title="无序列表">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
          <circle cx="2" cy="4" r="1.2" fill="currentColor"/>
          <circle cx="2" cy="8" r="1.2" fill="currentColor"/>
          <circle cx="2" cy="12" r="1.2" fill="currentColor"/>
          <path d="M5 4h9M5 8h9M5 12h9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
        </svg>
      </button>
      <button type="button" class="tool-btn" @mousedown.prevent="execCmd('insertOrderedList')" title="有序列表">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
          <text x="0" y="5.5" font-size="5" fill="currentColor" font-weight="bold">1.</text>
          <text x="0" y="9.5" font-size="5" fill="currentColor" font-weight="bold">2.</text>
          <text x="0" y="13.5" font-size="5" fill="currentColor" font-weight="bold">3.</text>
          <path d="M5 4h9M5 8h9M5 12h9" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
        </svg>
      </button>
      <button type="button" class="tool-btn" @mousedown.prevent="execCmd('removeFormat')" title="清除格式">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
          <path d="M3 12L9 3M6 12h7M3 6l7 0" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>
        </svg>
      </button>
    </div>

    <!-- Editable area -->
    <div class="editor-area-wrap">
      <div
        ref="editorRef"
        class="editor-area"
        contenteditable="true"
        :style="{ minHeight: (rows || 3) * 1.8 + 'em' }"
        @input="onInput"
        @focus="isFocused = true"
        @blur="isFocused = false"
        spellcheck="false"
      ></div>
      <div v-if="showPlaceholder" class="editor-placeholder">{{ placeholder || '请输入内容...' }}</div>
    </div>
  </div>
</template>

<style scoped>
.rich-editor-wrap {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--gray-50);
  overflow: hidden;
  transition: all var(--transition-fast);
}

.rich-editor-wrap.focused {
  border-color: var(--primary-400);
  background: white;
  box-shadow: 0 0 0 3px var(--primary-50);
}

/* Toolbar */
.rich-toolbar {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 4px 8px;
  background: white;
  border-bottom: 1px solid var(--border-color);
  flex-wrap: wrap;
}

.tool-btn {
  min-width: 26px;
  height: 24px;
  padding: 0 5px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid transparent;
  border-radius: 3px;
  background: transparent;
  cursor: pointer;
  color: var(--text-primary);
  font-size: 0.8rem;
  transition: all var(--transition-fast);
}

.tool-btn:hover {
  background: var(--gray-100);
  border-color: var(--gray-200);
}

.tool-btn.active {
  background: var(--primary-50);
  border-color: var(--primary-200);
  color: var(--primary-600);
}

.tool-divider {
  width: 1px;
  height: 16px;
  background: var(--gray-200);
  margin: 0 3px;
}

.tool-select {
  height: 24px;
  padding: 0 4px;
  border: 1px solid var(--gray-200);
  border-radius: 3px;
  font-size: 0.75rem;
  color: var(--text-primary);
  background: white;
  cursor: pointer;
  outline: none;
}

.tool-color {
  width: 24px;
  height: 24px;
  padding: 1px;
  border: 1px solid var(--gray-200);
  border-radius: 3px;
  cursor: pointer;
  background: white;
}

/* Editable area */
.editor-area-wrap {
  position: relative;
}

.editor-area {
  padding: 8px 10px;
  font-size: 0.88rem;
  line-height: 1.7;
  color: var(--text-primary);
  outline: none;
  word-break: break-word;
}

.editor-area:empty {
  min-height: 3em;
}

.editor-placeholder {
  position: absolute;
  top: 8px;
  left: 10px;
  color: var(--gray-400);
  font-size: 0.88rem;
  pointer-events: none;
  user-select: none;
}

/* List styles inside editor */
.editor-area :deep(ul) {
  list-style-type: disc;
  list-style-position: outside;
  padding-left: 16px;
  margin: 4px 0;
}

.editor-area :deep(ol) {
  list-style-type: decimal;
  list-style-position: outside;
  padding-left: 16px;
  margin: 4px 0;
}

.editor-area :deep(li) {
  display: list-item;
  margin-bottom: 2px;
  font-size: inherit;
}

.editor-area :deep(li)::marker {
  font-size: 1em;
  font-weight: inherit;
  color: currentColor;
}

@media (max-width: 760px) {
  .rich-toolbar {
    padding: 3px 6px;
  }

  .tool-btn {
    min-width: 24px;
    height: 22px;
  }

  .tool-select {
    height: 30px;
    min-width: 58px;
    line-height: 1.2;
  }

  .tool-color {
    width: 26px;
    height: 26px;
  }

  .editor-area {
    padding: 7px 9px;
    line-height: 1.55;
  }
}
</style>
