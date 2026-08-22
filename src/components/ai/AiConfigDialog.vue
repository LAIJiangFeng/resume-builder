<script setup lang="ts">
// author: jf
import { ref } from 'vue'
import { useAiConfigStore } from '@/stores/aiConfig'

const store = useAiConfigStore()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const useBackendSpeech = ref(store.useBackendSpeech)

function handleSave() {
  store.setUseBackendSpeech(useBackendSpeech.value)
  emit('close')
}

function handleCancel() {
  emit('close')
}
</script>

<template>
  <teleport to="body">
    <div class="dialog-overlay">
      <div class="dialog-card">
        <div class="dialog-header">
          <h3 class="dialog-title">
            <svg class="dialog-title-icon" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="3" />
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
            </svg>
            AI 配置
          </h3>
          <button class="dialog-close" @click="handleCancel">
            <svg class="icon-sm" viewBox="0 0 24 24"><path d="M18 6L6 18" /><path d="M6 6l12 12" /></svg>
          </button>
        </div>

        <p class="dialog-desc">当前仅保留实时语音配置，模型与 API 参数请在后端维护。启用后会优先尝试后端实时语音，失败时回退到浏览器免费语音识别。</p>

        <div class="dialog-body">
          <div class="form-group">
            <label class="form-label">语音路由</label>
            <label class="switch-row">
              <input v-model="useBackendSpeech" type="checkbox" />
              <span>启用后端实时语音优先链路</span>
            </label>
            <span class="form-hint">关闭后将始终使用浏览器免费语音识别，不再尝试后端实时语音。</span>
            <span v-if="store.backendSpeechAutoDisabled && useBackendSpeech" class="speech-status">
              后端实时语音链路在运行时连续失败后已自动停用。点击保存一次可重新尝试后端实时语音。
            </span>
          </div>
        </div>

        <div class="dialog-footer">
          <button class="btn-cancel" @click="handleCancel">取消</button>
          <button class="btn-save" @click="handleSave">保存配置</button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<style scoped>
.dialog-overlay {
  position: fixed;
  inset: 0;
  background: var(--overlay-backdrop);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.dialog-card {
  background: var(--surface-base);
  border-radius: 16px;
  width: 480px;
  max-width: 92vw;
  box-shadow: var(--shadow-dialog);
  animation: slideUp 0.25s ease;
}

@keyframes slideUp {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
}

.dialog-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.dialog-title-icon {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: var(--primary-500);
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
  flex-shrink: 0;
}

.icon-sm {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.dialog-close {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 8px;
  background: var(--surface-soft);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.dialog-close:hover {
  background: var(--primary-50);
  color: var(--primary-500);
}

.dialog-desc {
  padding: 8px 24px 0;
  font-size: 12px;
  color: var(--text-secondary);
  line-height: 1.5;
}

.dialog-body {
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-600);
}

.form-hint {
  font-size: 11px;
  color: var(--text-tertiary);
}

.switch-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--gray-600);
  user-select: none;
}

.switch-row input[type='checkbox'] {
  width: 14px;
  height: 14px;
}

.speech-status {
  margin-top: 4px;
  font-size: 11px;
  color: var(--primary-500);
  line-height: 1.4;
}

.dialog-footer {
  padding: 0 24px 20px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn-cancel {
  height: 38px;
  padding: 0 18px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--surface-base);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-cancel:hover {
  border-color: var(--primary-500);
  color: var(--primary-500);
}

.btn-save {
  height: 38px;
  padding: 0 20px;
  border-radius: 8px;
  border: none;
  background: var(--primary-500);
  color: var(--text-inverse);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-save:hover {
  background: var(--primary-600);
}

@media (max-width: 520px) {
  .dialog-overlay {
    align-items: flex-end;
    padding: 10px;
  }

  .dialog-card {
    width: 100%;
    max-width: none;
    border-radius: 18px;
  }

  .dialog-header {
    padding: 16px 16px 0;
  }

  .dialog-desc,
  .dialog-body {
    padding-inline: 16px;
  }

  .dialog-footer {
    padding: 0 16px calc(16px + env(safe-area-inset-bottom));
  }

  .btn-cancel,
  .btn-save {
    flex: 1;
    min-width: 0;
  }
}
</style>
