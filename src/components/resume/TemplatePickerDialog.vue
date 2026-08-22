<script setup lang="ts">
// author: jf
import { ref } from 'vue'
import type { ResumeTemplateDefinition, ResumeTemplateKey } from '@/templates/resume'

const props = defineProps<{
  modelValue: boolean
  templates: ResumeTemplateDefinition[]
  selectedKey: ResumeTemplateKey
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'select', key: ResumeTemplateKey): void
}>()

const brokenTemplateImageKeys = ref<Set<string>>(new Set())

function closeDialog() {
  emit('update:modelValue', false)
}

function chooseTemplate(key: ResumeTemplateKey) {
  emit('select', key)
  emit('update:modelValue', false)
}

function isTemplateImageBroken(key: string): boolean {
  return brokenTemplateImageKeys.value.has(key)
}

function markTemplateImageBroken(key: string) {
  if (brokenTemplateImageKeys.value.has(key)) return
  const next = new Set(brokenTemplateImageKeys.value)
  next.add(key)
  brokenTemplateImageKeys.value = next
}

function resolvePreviewImageSrc(value: string): string {
  const src = value.trim()
  if (!src) return ''
  if (src.startsWith('//')) return `https:${src}`
  if (/^(https?:|data:|blob:)/i.test(src)) return src
  return src
}
</script>

<template>
  <div v-if="props.modelValue" class="template-picker-mask" @click.self="closeDialog">
    <div class="template-picker-dialog">
      <div class="template-picker-head">
        <span>选择模板</span>
        <button class="template-picker-close" type="button" aria-label="关闭模板选择" title="关闭" @click="closeDialog">
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M6 6l12 12M18 6 6 18" />
          </svg>
        </button>
      </div>
      <div class="template-picker-list">
        <button
          v-for="item in props.templates"
          :key="item.key"
          class="template-picker-item"
          :class="{ 'template-picker-item-active': item.key === props.selectedKey }"
          @click="chooseTemplate(item.key)"
        >
          <div class="template-thumb">
            <img
              v-if="item.previewImage && !isTemplateImageBroken(item.key)"
              :src="resolvePreviewImageSrc(item.previewImage)"
              :alt="`${item.name}预览图`"
              loading="lazy"
              referrerpolicy="no-referrer"
              @error="markTemplateImageBroken(item.key)"
            />
            <div v-else class="template-thumb-fallback">A4</div>
          </div>
          <div class="template-info">
            <p class="template-name">{{ item.name }}</p>
            <span class="template-badge">A4</span>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.template-picker-mask {
  position: fixed;
  inset: 0;
  background: var(--overlay-backdrop);
  z-index: 1000;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 18px;
}

.template-picker-dialog {
  width: min(980px, calc(100vw - 36px));
  max-height: min(86vh, 960px);
  overflow: hidden;
  border-radius: 16px;
  background: var(--surface-base);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-dialog);
  display: flex;
  flex-direction: column;
}

.template-picker-head {
  height: 56px;
  padding: 0 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 700;
}

.template-picker-close {
  border: 1px solid var(--border-color);
  background: var(--surface-base);
  color: var(--text-secondary);
  border-radius: 8px;
  width: 30px;
  height: 30px;
  padding: 0;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.template-picker-close:hover {
  background: var(--primary-50);
  color: var(--primary-500);
}

.template-picker-close svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
}

.template-picker-list {
  padding: 16px;
  overflow: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 14px;
}

.template-picker-item {
  border: 1px solid var(--border-color);
  border-radius: 12px;
  background: var(--surface-base);
  padding: 10px;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.12s ease, box-shadow 0.12s ease, background-color 0.12s ease;
}

.template-picker-item:hover {
  border-color: var(--primary-500);
  background: var(--surface-soft);
  box-shadow: var(--shadow-lg);
}

.template-picker-item-active {
  border-color: var(--primary-500);
  box-shadow: 0 0 0 1px var(--theme-focus-ring);
}

.template-thumb {
  width: 100%;
  aspect-ratio: 4 / 5;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border-color);
  background: var(--surface-soft);
}

.template-thumb img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.template-thumb-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 800;
  color: var(--text-secondary);
  background: var(--template-placeholder-gradient);
}

.template-info {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.template-name {
  margin: 0;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.3;
}

.template-badge {
  flex-shrink: 0;
  height: 22px;
  padding: 0 8px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
}

@media (max-width: 720px) {
  .template-picker-mask {
    align-items: flex-end;
    padding: 8px;
  }

  .template-picker-dialog {
    width: 100%;
    max-height: min(84dvh, 720px);
    border-radius: 14px;
  }

  .template-picker-head {
    min-height: 46px;
    height: auto;
    padding: 7px 10px;
    font-size: 14px;
  }

  .template-picker-close {
    width: 28px;
    height: 28px;
    border-radius: 7px;
  }

  .template-picker-list {
    grid-template-columns: repeat(auto-fit, minmax(clamp(118px, 42vw, 176px), 1fr));
    gap: 8px;
    padding: 9px;
  }

  .template-picker-item {
    padding: 6px;
    min-width: 0;
  }

  .template-info {
    margin-top: 7px;
    gap: 6px;
  }

  .template-name {
    font-size: 13px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .template-badge {
    height: 20px;
    padding: 0 6px;
    font-size: 11px;
  }
}

@media (max-width: 420px) {
  .template-picker-list {
    grid-template-columns: repeat(auto-fit, minmax(clamp(108px, 44vw, 150px), 1fr));
    gap: 7px;
    padding: 8px;
  }

  .template-picker-item {
    border-radius: 10px;
    padding: 5px;
  }

  .template-thumb {
    border-radius: 7px;
  }

  .template-name {
    font-size: 12px;
  }

  .template-badge {
    height: 18px;
    padding: 0 5px;
    font-size: 10px;
  }
}
</style>
