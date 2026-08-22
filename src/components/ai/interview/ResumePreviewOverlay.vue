<script setup lang="ts">
// author: jf
import { computed } from 'vue'
import { useResumeStore } from '@/stores/resume'
import { getResumeTemplateByKey, type ResumeTemplateDefinition } from '@/templates/resume'

const emit = defineEmits<{
  (e: 'close'): void
}>()

const store = useResumeStore()

const fallbackTemplate: ResumeTemplateDefinition = getResumeTemplateByKey('default')
const currentTemplate = computed<ResumeTemplateDefinition>(
  () => getResumeTemplateByKey(store.selectedTemplateKey) ?? fallbackTemplate
)
const currentTemplateComponent = computed(() => currentTemplate.value.component)
</script>

<template>
  <section class="resume-overlay">
    <header class="overlay-header">
      <h3 class="overlay-title">简历实时预览</h3>
      <button class="close-btn" type="button" aria-label="关闭简历预览" @click="emit('close')">×</button>
    </header>

    <div class="overlay-body">
      <div class="paper-shell">
        <div class="paper">
          <component :is="currentTemplateComponent" />
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.resume-overlay {
  position: absolute;
  right: 12px;
  top: 12px;
  bottom: clamp(150px, 18vh, 210px);
  width: min(760px, calc(100% - 24px));
  border-radius: 14px;
  border: 1px solid var(--border-color);
  background: var(--surface-base);
  box-shadow: var(--shadow-dialog);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 12;
}

.overlay-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.overlay-title {
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 700;
}

.close-btn {
  width: 24px;
  height: 24px;
  border-radius: 7px;
  border: none;
  background: var(--primary-50);
  color: var(--primary-500);
  font-size: 15px;
  font-weight: 700;
  line-height: 1;
  cursor: pointer;
}

.overlay-body {
  flex: 1;
  min-height: 0;
  border-radius: 12px;
  background: var(--surface-disabled);
  padding: 10px;
}

.paper-shell {
  width: 100%;
  height: 100%;
  overflow: auto;
}

.paper {
  width: 100%;
  min-height: 100%;
  background: var(--resume-paper-background);
  border-radius: 6px;
  border: 1px solid var(--resume-paper-border);
  box-shadow: var(--resume-paper-shadow);
}

.paper :deep([class*='resume-template-']) {
  min-height: 100%;
}

@media (max-width: 1280px) {
  .resume-overlay {
    width: calc(100% - 24px);
    left: 12px;
    right: 12px;
  }
}

@media (max-width: 720px) {
  .resume-overlay {
    position: fixed;
    inset: 10px 10px calc(86px + env(safe-area-inset-bottom)) 10px;
    width: auto;
    border-radius: 18px;
    padding: 10px;
    z-index: 220;
  }

  .overlay-body {
    padding: 8px;
  }

  .paper-shell {
    overflow-x: hidden;
  }

  .paper {
    overflow: hidden;
  }

  .paper :deep(.resume-header) {
    gap: 10px;
  }

  .paper :deep(.header-main) {
    min-width: 0;
  }

  .paper :deep(.resume-header .avatar-wrap),
  .paper :deep(.photo-frame) {
    width: clamp(58px, 18vw, 72px) !important;
    height: clamp(72px, 23vw, 90px) !important;
  }

  .paper :deep(.hero-bg .avatar-wrap) {
    width: clamp(58px, 18vw, 72px) !important;
    height: clamp(58px, 18vw, 72px) !important;
    border-width: 3px !important;
  }

  .close-btn {
    width: 34px;
    height: 34px;
  }
}
</style>
