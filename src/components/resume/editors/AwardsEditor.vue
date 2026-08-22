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
        <h3>荣誉奖项</h3>
      </div>
    </div>

    <div v-show="!collapsed" class="section-body">
      <div
        v-for="(award, index) in store.awardList"
        :key="award.id"
        class="entry-card"
      >
        <div class="entry-header">
          <span class="entry-index">奖项 {{ index + 1 }}</span>
          <button class="btn-remove" @click="store.removeAward(award.id)">✕</button>
        </div>

        <div class="form-grid">
          <div class="form-group">
            <label class="form-label">奖项名称</label>
            <input v-model="award.name" type="text" class="form-input" placeholder="例如：国家奖学金" />
          </div>
          <div class="form-group">
            <label class="form-label">获奖时间</label>
            <input v-model="award.date" type="month" class="form-input" />
          </div>
        </div>
        <div class="form-group form-group-full">
          <label class="form-label">描述</label>
          <RichEditor v-model="award.description" :rows="2" placeholder="简要描述..." />
        </div>
      </div>

      <button class="btn-add" @click="store.addAward()">
        <span class="btn-add-icon">+</span>
        添加荣誉奖项
      </button>
    </div>
  </section>
</template>

<style scoped>
.editor-section{margin-bottom:var(--spacing-lg);border:1px solid var(--border-color);border-radius:var(--radius-lg);background:var(--surface-base);overflow:hidden;transition:box-shadow var(--transition-base)}.editor-section:hover{box-shadow:var(--shadow-sm)}.section-header{display:flex;align-items:center;justify-content:space-between;padding:var(--spacing-lg) var(--spacing-xl);cursor:pointer;user-select:none;transition:background var(--transition-fast)}.section-header:hover{background:var(--gray-50)}.section-toggle{display:flex;align-items:center;gap:var(--spacing-sm)}.section-toggle h3{font-size:.95rem;font-weight:600;color:var(--text-primary)}.chevron{color:var(--text-secondary);transition:transform var(--transition-base);transform:rotate(0deg)}.chevron.rotated{transform:rotate(90deg)}.section-body{padding:0 var(--spacing-xl) var(--spacing-xl)}.entry-card{padding:var(--spacing-lg);margin-bottom:var(--spacing-md);background:var(--gray-50);border-radius:var(--radius-md);border:1px solid var(--gray-100)}.entry-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--spacing-md)}.entry-index{font-size:.82rem;font-weight:600;color:var(--primary-600)}.btn-remove{width:24px;height:24px;display:flex;align-items:center;justify-content:center;border:none;background:var(--gray-200);color:var(--gray-500);border-radius:50%;cursor:pointer;font-size:.7rem;transition:all var(--transition-fast)}.btn-remove:hover{background:var(--accent-red);color:var(--text-inverse)}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:var(--spacing-md) var(--spacing-lg)}.form-group{display:flex;flex-direction:column;gap:var(--spacing-xs)}.form-group-full{margin-top:var(--spacing-md)}.form-label{font-size:.78rem;font-weight:500;color:var(--text-secondary)}.form-input{padding:var(--spacing-sm) var(--spacing-md);border:1px solid var(--border-color);border-radius:var(--radius-md);font-size:.88rem;color:var(--text-primary);background:var(--surface-base);transition:all var(--transition-fast);outline:none}.form-input:focus{border-color:var(--primary-400);box-shadow:0 0 0 3px var(--primary-50)}.form-textarea{width:100%;padding:var(--spacing-sm) var(--spacing-md);border:1px solid var(--border-color);border-radius:var(--radius-md);font-size:.88rem;color:var(--text-primary);background:var(--surface-base);transition:all var(--transition-fast);outline:none;resize:vertical;line-height:1.6}.form-textarea:focus{border-color:var(--primary-400);box-shadow:0 0 0 3px var(--primary-50)}.btn-add{display:flex;align-items:center;justify-content:center;gap:var(--spacing-sm);width:100%;padding:var(--spacing-md);border:2px dashed var(--primary-200);border-radius:var(--radius-md);background:transparent;color:var(--primary-600);font-size:.88rem;font-weight:500;cursor:pointer;transition:all var(--transition-fast)}.btn-add:hover{background:var(--primary-50);border-color:var(--primary-400)}.btn-add-icon{font-size:1.1rem;font-weight:700}
</style>
