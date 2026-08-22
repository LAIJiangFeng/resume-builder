<script setup lang="ts">
// author: jf
import { useResumeStore } from '@/stores/resume'
import { ref } from 'vue'
import RichEditor from '@/components/common/RichEditor.vue'

const store = useResumeStore()
const collapsed = ref(false)
</script>

<template>
  <section class="editor-section">
    <div class="section-header" @click="collapsed = !collapsed">
      <div class="section-toggle">
        <svg class="chevron" :class="{ rotated: !collapsed }" width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M6 4L10 8L6 12" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <h3>个人简介</h3>
      </div>
    </div>

    <div v-show="!collapsed" class="section-body">
      <div class="form-group">
        <label class="form-label">自我介绍</label>
        <RichEditor
          v-model="store.selfIntro"
          :rows="6"
          placeholder="简要介绍自己的职业背景、核心能力和求职目标..."
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
.editor-section{margin-bottom:var(--spacing-lg);border:1px solid var(--border-color);border-radius:var(--radius-lg);background:var(--surface-base);overflow:hidden;transition:box-shadow var(--transition-base)}.editor-section:hover{box-shadow:var(--shadow-sm)}.section-header{display:flex;align-items:center;justify-content:space-between;padding:var(--spacing-lg) var(--spacing-xl);cursor:pointer;user-select:none;transition:background var(--transition-fast)}.section-header:hover{background:var(--gray-50)}.section-toggle{display:flex;align-items:center;gap:var(--spacing-sm)}.section-toggle h3{font-size:.95rem;font-weight:600;color:var(--text-primary)}.chevron{color:var(--text-secondary);transition:transform var(--transition-base);transform:rotate(0deg)}.chevron.rotated{transform:rotate(90deg)}.section-body{padding:0 var(--spacing-xl) var(--spacing-xl)}.form-group{display:flex;flex-direction:column;gap:var(--spacing-xs)}.form-label{font-size:.78rem;font-weight:500;color:var(--text-secondary)}.form-textarea{width:100%;padding:var(--spacing-md);border:1px solid var(--border-color);border-radius:var(--radius-md);font-size:.88rem;color:var(--text-primary);background:var(--gray-50);transition:all var(--transition-fast);outline:none;resize:vertical;line-height:1.8;font-family:var(--font-sans)}.form-textarea:focus{border-color:var(--primary-400);background:var(--surface-base);box-shadow:0 0 0 3px var(--primary-50)}
</style>
