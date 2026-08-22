<!-- author: jf -->
<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { CheckCircle2, Eye, EyeOff, KeyRound, LockKeyhole, Mail, ShieldCheck, X } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{
  open: boolean
  initialEmail?: string
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'reset-success', email: string): void
}>()

const authStore = useAuthStore()
const dialogRef = ref<HTMLElement | null>(null)
const email = ref('')
const verificationCode = ref('')
const newPassword = ref('')
const confirmPassword = ref('')
const showNewPassword = ref(false)
const showConfirmPassword = ref(false)
const errorMessage = ref('')
const statusMessage = ref('')
const isSendingCode = ref(false)
const isSubmitting = ref(false)
const isComplete = ref(false)
const cooldownSeconds = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | null = null
let previousActiveElement: HTMLElement | null = null
let previousBodyOverflow = ''
let isScrollLocked = false

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const emailCodeButtonLabel = computed(() => {
  if (isSendingCode.value) return '发送中...'
  if (cooldownSeconds.value > 0) return `${cooldownSeconds.value}s 后重发`
  return '发送验证码'
})

function resetFeedback() {
  errorMessage.value = ''
  statusMessage.value = ''
}

function clearCooldownTimer() {
  if (cooldownTimer !== null) {
    clearInterval(cooldownTimer)
    cooldownTimer = null
  }
}

function startCooldown(seconds: number) {
  clearCooldownTimer()
  cooldownSeconds.value = Math.max(0, Math.floor(seconds))
  if (cooldownSeconds.value <= 0) return

  cooldownTimer = setInterval(() => {
    cooldownSeconds.value = Math.max(0, cooldownSeconds.value - 1)
    if (cooldownSeconds.value === 0) clearCooldownTimer()
  }, 1000)
}

function initializeDialog() {
  const safeInitialEmail = props.initialEmail?.trim().toLowerCase() ?? ''
  email.value = EMAIL_PATTERN.test(safeInitialEmail) ? safeInitialEmail : ''
  verificationCode.value = ''
  newPassword.value = ''
  confirmPassword.value = ''
  showNewPassword.value = false
  showConfirmPassword.value = false
  errorMessage.value = ''
  statusMessage.value = ''
  isSendingCode.value = false
  isSubmitting.value = false
  isComplete.value = false
  cooldownSeconds.value = 0
  clearCooldownTimer()
}

function restorePageScroll() {
  if (!isScrollLocked) return
  document.body.style.overflow = previousBodyOverflow
  isScrollLocked = false
}

function closeDialog() {
  if (isSendingCode.value || isSubmitting.value) return
  emit('close')
}

function finishReset() {
  emit('reset-success', email.value.trim().toLowerCase())
}

function handleEmailInput() {
  verificationCode.value = ''
  cooldownSeconds.value = 0
  clearCooldownTimer()
  resetFeedback()
}

function handleVerificationCodeInput(event: Event) {
  const target = event.target as HTMLInputElement
  const normalizedCode = target.value.replace(/\D/g, '').slice(0, 6)
  target.value = normalizedCode
  verificationCode.value = normalizedCode
  resetFeedback()
}

async function handleSendEmailCode() {
  if (isSendingCode.value || isSubmitting.value || cooldownSeconds.value > 0) return
  resetFeedback()

  const requestedEmail = email.value.trim().toLowerCase()
  if (!EMAIL_PATTERN.test(requestedEmail)) {
    errorMessage.value = '请输入注册时使用的正确邮箱地址。'
    return
  }

  isSendingCode.value = true
  statusMessage.value = '正在发送重置密码验证码...'
  try {
    const result = await authStore.sendPasswordResetEmailCode(requestedEmail)
    startCooldown(result.cooldownSeconds)
    const validMinutes = Math.max(1, Math.ceil(result.expiresInSeconds / 60))
    statusMessage.value = `如果该邮箱已注册，验证码将在短时间内送达，${validMinutes} 分钟内有效。`
  } catch (error) {
    const message = error instanceof Error ? error.message : '验证码发送服务不可用，请稍后重试。'
    statusMessage.value = ''
    errorMessage.value = `验证码发送失败：${message}`
  } finally {
    isSendingCode.value = false
  }
}

async function handleSubmit() {
  if (isSubmitting.value || isSendingCode.value) return
  resetFeedback()

  const requestedEmail = email.value.trim().toLowerCase()
  if (!EMAIL_PATTERN.test(requestedEmail)) {
    errorMessage.value = '请输入注册时使用的正确邮箱地址。'
    return
  }
  if (!/^\d{6}$/.test(verificationCode.value)) {
    errorMessage.value = '请输入邮件中的 6 位验证码。'
    return
  }
  if (newPassword.value.length < 8 || newPassword.value.length > 128) {
    errorMessage.value = '新密码长度需要在 8 到 128 位之间。'
    return
  }
  if (newPassword.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的新密码不一致。'
    return
  }

  isSubmitting.value = true
  try {
    await authStore.resetPassword(requestedEmail, verificationCode.value, newPassword.value)
    clearCooldownTimer()
    isComplete.value = true
  } catch (error) {
    const message = error instanceof Error ? error.message : '密码重置服务不可用，请稍后重试。'
    errorMessage.value = `密码重置失败：${message}`
  } finally {
    isSubmitting.value = false
  }
}

function handleWindowKeydown(event: KeyboardEvent) {
  if (!props.open) return

  if (event.key === 'Escape') {
    event.preventDefault()
    closeDialog()
    return
  }
  if (event.key !== 'Tab' || !dialogRef.value) return

  const focusableElements = Array.from(
    dialogRef.value.querySelectorAll<HTMLElement>(
      'button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  )
  if (focusableElements.length === 0) return

  const firstElement = focusableElements[0]
  const lastElement = focusableElements[focusableElements.length - 1]
  if (event.shiftKey && document.activeElement === firstElement) {
    event.preventDefault()
    lastElement?.focus()
  } else if (!event.shiftKey && document.activeElement === lastElement) {
    event.preventDefault()
    firstElement?.focus()
  }
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      initializeDialog()
      previousActiveElement = document.activeElement instanceof HTMLElement ? document.activeElement : null
      previousBodyOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      isScrollLocked = true
      await nextTick()
      dialogRef.value?.focus()
      return
    }

    clearCooldownTimer()
    restorePageScroll()
    if (previousActiveElement?.isConnected) previousActiveElement.focus()
    previousActiveElement = null
  },
)

onMounted(() => window.addEventListener('keydown', handleWindowKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleWindowKeydown)
  clearCooldownTimer()
  restorePageScroll()
})
</script>

<template>
  <Teleport to="body">
    <Transition name="forgot-password-dialog">
      <div v-if="open" class="forgot-password-layer" @click.self="closeDialog">
        <section
          ref="dialogRef"
          class="forgot-password-dialog"
          role="dialog"
          aria-modal="true"
          aria-labelledby="forgot-password-title"
          tabindex="-1"
        >
          <header class="forgot-password-header">
            <div class="forgot-password-heading">
              <span class="forgot-password-icon" aria-hidden="true">
                <KeyRound :size="22" stroke-width="1.9" />
              </span>
              <div>
                <span>ACCOUNT RECOVERY</span>
                <h2 id="forgot-password-title">邮箱验证重置密码</h2>
              </div>
            </div>
            <button
              class="forgot-password-close"
              type="button"
              :disabled="isSendingCode || isSubmitting"
              aria-label="关闭重置密码弹窗"
              @click="closeDialog"
            >
              <X :size="20" stroke-width="1.9" aria-hidden="true" />
            </button>
          </header>

          <div v-if="isComplete" class="reset-complete">
            <span class="reset-complete-icon" aria-hidden="true">
              <CheckCircle2 :size="34" stroke-width="1.8" />
            </span>
            <h3>密码已重置</h3>
            <p>新密码已经生效，原有登录凭据也已失效。请返回登录页使用新密码登录。</p>
            <button type="button" @click="finishReset">返回登录</button>
          </div>

          <form v-else class="forgot-password-form" :aria-busy="isSendingCode || isSubmitting" @submit.prevent="handleSubmit">
            <p class="forgot-password-summary">验证注册邮箱后即可设置新密码，验证码不会通过其他方式向你索取。</p>

            <div class="reset-step-heading">
              <span>01</span>
              <div>
                <strong>验证注册邮箱</strong>
                <p>验证码将发送到你的注册邮箱。</p>
              </div>
            </div>

            <div class="field-shell">
              <label class="sr-only" for="reset-email">注册邮箱</label>
              <Mail :size="19" stroke-width="1.8" aria-hidden="true" />
              <input
                id="reset-email"
                v-model.trim="email"
                type="email"
                autocomplete="email"
                placeholder="注册邮箱"
                :disabled="isSendingCode || isSubmitting"
                @input="handleEmailInput"
              />
            </div>

            <div class="field-shell verification-shell">
              <label class="sr-only" for="reset-verification-code">邮箱验证码</label>
              <ShieldCheck :size="19" stroke-width="1.8" aria-hidden="true" />
              <input
                id="reset-verification-code"
                v-model="verificationCode"
                type="text"
                inputmode="numeric"
                autocomplete="one-time-code"
                maxlength="6"
                placeholder="6 位验证码"
                :disabled="isSubmitting"
                @input="handleVerificationCodeInput"
              />
              <button
                class="verification-action"
                type="button"
                :disabled="isSendingCode || isSubmitting || cooldownSeconds > 0"
                @click="handleSendEmailCode"
              >
                {{ emailCodeButtonLabel }}
              </button>
            </div>

            <div class="reset-step-heading password-step">
              <span>02</span>
              <div>
                <strong>设置新密码</strong>
                <p>密码长度为 8 到 128 位。</p>
              </div>
            </div>

            <div class="field-shell">
              <label class="sr-only" for="reset-new-password">新密码</label>
              <LockKeyhole :size="19" stroke-width="1.8" aria-hidden="true" />
              <input
                id="reset-new-password"
                v-model="newPassword"
                :type="showNewPassword ? 'text' : 'password'"
                autocomplete="new-password"
                placeholder="新密码"
                minlength="8"
                maxlength="128"
                :disabled="isSubmitting"
                @input="resetFeedback"
              />
              <button
                class="password-toggle"
                type="button"
                :aria-label="showNewPassword ? '隐藏新密码' : '显示新密码'"
                @click="showNewPassword = !showNewPassword"
              >
                <Eye v-if="showNewPassword" :size="18" stroke-width="1.9" aria-hidden="true" />
                <EyeOff v-else :size="18" stroke-width="1.9" aria-hidden="true" />
              </button>
            </div>

            <div class="field-shell">
              <label class="sr-only" for="reset-confirm-password">确认新密码</label>
              <LockKeyhole :size="19" stroke-width="1.8" aria-hidden="true" />
              <input
                id="reset-confirm-password"
                v-model="confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                autocomplete="new-password"
                placeholder="再次输入新密码"
                minlength="8"
                maxlength="128"
                :disabled="isSubmitting"
                @input="resetFeedback"
              />
              <button
                class="password-toggle"
                type="button"
                :aria-label="showConfirmPassword ? '隐藏确认密码' : '显示确认密码'"
                @click="showConfirmPassword = !showConfirmPassword"
              >
                <Eye v-if="showConfirmPassword" :size="18" stroke-width="1.9" aria-hidden="true" />
                <EyeOff v-else :size="18" stroke-width="1.9" aria-hidden="true" />
              </button>
            </div>

            <p v-if="errorMessage" class="reset-error" role="alert">{{ errorMessage }}</p>
            <p v-if="statusMessage" class="reset-status" role="status" aria-live="polite">
              <CheckCircle2 :size="16" stroke-width="1.9" aria-hidden="true" />
              <span>{{ statusMessage }}</span>
            </p>

            <div class="forgot-password-actions">
              <button class="reset-secondary" type="button" :disabled="isSendingCode || isSubmitting" @click="closeDialog">
                返回登录
              </button>
              <button class="reset-primary" type="submit" :disabled="isSendingCode || isSubmitting">
                {{ isSubmitting ? '重置中...' : '确认重置密码' }}
              </button>
            </div>
          </form>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.forgot-password-layer {
  position: fixed;
  inset: 0;
  z-index: 2100;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.58);
  backdrop-filter: blur(10px);
}

.forgot-password-dialog {
  position: relative;
  display: flex;
  width: min(540px, 100%);
  max-height: min(860px, calc(100dvh - 48px));
  overflow: hidden;
  flex-direction: column;
  border: 1px solid var(--border-color, #dbe3ef);
  border-radius: 28px;
  outline: none;
  background: var(--surface-base, #fff);
  color: var(--text-primary, #0f172a);
  box-shadow: 0 30px 90px rgba(15, 23, 42, 0.28);
}

.forgot-password-dialog::before {
  position: absolute;
  z-index: 1;
  top: 0;
  right: 0;
  left: 0;
  height: 4px;
  background: var(--primary-500, #2563eb);
  content: '';
}

.forgot-password-header {
  display: flex;
  flex: 0 0 auto;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  padding: 28px 30px 22px;
  border-bottom: 1px solid var(--border-soft, #edf1f6);
}

.forgot-password-heading {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 14px;
}

.forgot-password-icon {
  display: grid;
  width: 46px;
  height: 46px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--primary-500, #2563eb) 18%, transparent);
  border-radius: 14px;
  background: var(--primary-50, #eff6ff);
  color: var(--primary-500, #2563eb);
}

.forgot-password-heading span:not(.forgot-password-icon) {
  display: block;
  margin-bottom: 5px;
  color: var(--primary-500, #2563eb);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
}

.forgot-password-heading h2 {
  margin: 0;
  font-size: clamp(21px, 3vw, 27px);
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.2;
}

.forgot-password-close {
  display: grid;
  width: 38px;
  height: 38px;
  flex: 0 0 auto;
  place-items: center;
  border: 1px solid var(--border-color, #dbe3ef);
  border-radius: 12px;
  background: var(--surface-base, #fff);
  color: var(--text-secondary, #475569);
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    color 0.18s ease,
    background 0.18s ease;
}

.forgot-password-close:hover,
.forgot-password-close:focus-visible {
  border-color: var(--primary-500, #2563eb);
  background: var(--primary-50, #eff6ff);
  color: var(--primary-500, #2563eb);
}

.forgot-password-close:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.forgot-password-form {
  display: grid;
  width: 100%;
  min-height: 0;
  min-width: 0;
  grid-template-columns: minmax(0, 1fr);
  gap: 14px;
  padding: 24px 30px 28px;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-color: var(--border-color, #cbd5e1) transparent;
  scrollbar-width: thin;
}

.forgot-password-form > * {
  min-width: 0;
  max-width: 100%;
}

.forgot-password-summary {
  margin: 0 0 3px;
  color: var(--text-secondary, #475569);
  font-size: 14px;
  line-height: 1.7;
  overflow-wrap: anywhere;
}

.reset-step-heading {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  align-items: start;
  gap: 11px;
  margin-top: 5px;
}

.reset-step-heading.password-step {
  margin-top: 10px;
}

.reset-step-heading > span {
  display: grid;
  width: 32px;
  height: 26px;
  place-items: center;
  border-radius: 8px;
  background: var(--primary-50, #eff6ff);
  color: var(--primary-500, #2563eb);
  font-size: 11px;
  font-weight: 700;
}

.reset-step-heading strong {
  display: block;
  font-size: 14px;
  line-height: 1.35;
}

.reset-step-heading p {
  margin: 3px 0 0;
  color: var(--text-tertiary, #64748b);
  font-size: 12px;
  line-height: 1.4;
}

.field-shell {
  display: flex;
  width: 100%;
  height: 54px;
  min-width: 0;
  max-width: 100%;
  align-items: center;
  gap: 11px;
  padding: 0 16px;
  border: 1px solid var(--border-color, #dbe3ef);
  border-radius: 15px;
  background: var(--surface-soft, #f8fafc);
  color: var(--text-secondary, #475569);
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.field-shell:focus-within {
  border-color: var(--primary-500, #2563eb);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary-500, #2563eb) 14%, transparent);
}

.field-shell > svg {
  flex: 0 0 auto;
}

.field-shell input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text-primary, #0f172a);
  font: inherit;
  font-size: 14px;
}

.verification-shell input {
  width: 0;
  min-width: 0;
  flex: 1 1 0;
}

.field-shell input::placeholder {
  color: var(--text-tertiary, #64748b);
}

.field-shell input:disabled {
  cursor: not-allowed;
}

.verification-action {
  height: 34px;
  min-width: 98px;
  flex: 0 0 auto;
  padding: 0 12px;
  border: 0;
  border-radius: 10px;
  background: var(--primary-500, #2563eb);
  color: #fff;
  font-size: 12px;
  font-weight: 650;
  white-space: nowrap;
  cursor: pointer;
}

.verification-action:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.password-toggle {
  display: inline-flex;
  padding: 4px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-secondary, #475569);
  cursor: pointer;
}

.password-toggle:hover,
.password-toggle:focus-visible {
  background: var(--primary-50, #eff6ff);
  color: var(--primary-500, #2563eb);
}

.reset-error,
.reset-status {
  margin: 2px 0 0;
  font-size: 13px;
  line-height: 1.55;
}

.reset-error {
  color: var(--text-danger, #b42318);
  font-weight: 600;
}

.reset-status {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 11px 12px;
  border: 1px solid color-mix(in srgb, var(--primary-500, #2563eb) 18%, transparent);
  border-radius: 12px;
  background: var(--primary-50, #eff6ff);
  color: var(--text-secondary, #475569);
}

.reset-status svg {
  flex: 0 0 auto;
  margin-top: 2px;
  color: var(--primary-500, #2563eb);
}

.forgot-password-actions {
  display: grid;
  width: 100%;
  min-width: 0;
  grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.35fr);
  gap: 10px;
  margin-top: 8px;
}

.reset-secondary,
.reset-primary,
.reset-complete button {
  min-width: 0;
  height: 44px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.reset-secondary {
  border: 1px solid var(--border-color, #dbe3ef);
  background: var(--surface-base, #fff);
  color: var(--text-secondary, #475569);
}

.reset-primary,
.reset-complete button {
  border: 1px solid var(--primary-500, #2563eb);
  background: var(--primary-500, #2563eb);
  color: #fff;
  box-shadow: 0 10px 24px color-mix(in srgb, var(--primary-500, #2563eb) 22%, transparent);
}

.reset-secondary:hover,
.reset-secondary:focus-visible {
  border-color: var(--primary-500, #2563eb);
  color: var(--primary-500, #2563eb);
}

.reset-primary:hover,
.reset-primary:focus-visible,
.reset-complete button:hover,
.reset-complete button:focus-visible {
  transform: translateY(-1px);
  box-shadow: 0 14px 28px color-mix(in srgb, var(--primary-500, #2563eb) 28%, transparent);
}

.reset-secondary:disabled,
.reset-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  transform: none;
}

.reset-complete {
  display: grid;
  justify-items: center;
  padding: 54px 42px 48px;
  text-align: center;
}

.reset-complete-icon {
  display: grid;
  width: 70px;
  height: 70px;
  place-items: center;
  border: 1px solid color-mix(in srgb, var(--primary-500, #2563eb) 20%, transparent);
  border-radius: 22px;
  background: var(--primary-50, #eff6ff);
  color: var(--primary-500, #2563eb);
}

.reset-complete h3 {
  margin: 22px 0 8px;
  font-size: 24px;
  font-weight: 700;
}

.reset-complete p {
  max-width: 380px;
  margin: 0;
  color: var(--text-secondary, #475569);
  font-size: 14px;
  line-height: 1.75;
}

.reset-complete button {
  width: min(240px, 100%);
  margin-top: 26px;
}

.forgot-password-close:focus-visible,
.verification-action:focus-visible,
.password-toggle:focus-visible,
.reset-secondary:focus-visible,
.reset-primary:focus-visible,
.reset-complete button:focus-visible {
  outline: 2px solid var(--primary-500, #2563eb);
  outline-offset: 3px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.forgot-password-dialog-enter-active,
.forgot-password-dialog-leave-active {
  transition: opacity 0.2s ease;
}

.forgot-password-dialog-enter-active .forgot-password-dialog,
.forgot-password-dialog-leave-active .forgot-password-dialog {
  transition:
    opacity 0.2s ease,
    transform 0.22s ease;
}

.forgot-password-dialog-enter-from,
.forgot-password-dialog-leave-to {
  opacity: 0;
}

.forgot-password-dialog-enter-from .forgot-password-dialog,
.forgot-password-dialog-leave-to .forgot-password-dialog {
  opacity: 0;
  transform: translateY(12px) scale(0.985);
}

@media (max-width: 620px) {
  .forgot-password-layer {
    align-items: end;
    padding: 12px;
  }

  .forgot-password-dialog {
    width: calc(100vw - 24px);
    max-width: 540px;
    max-height: calc(100dvh - 24px);
    border-radius: 22px;
  }

  .forgot-password-header {
    padding: 23px 20px 18px;
  }

  .forgot-password-icon {
    width: 40px;
    height: 40px;
    border-radius: 12px;
  }

  .forgot-password-form {
    min-width: 0;
    padding: 20px;
  }

  .verification-shell {
    height: 54px;
    min-height: 54px;
    flex-wrap: nowrap;
    padding-top: 0;
    padding-bottom: 0;
  }

  .verification-shell input {
    width: 0;
    min-width: 0;
    flex: 1 1 0;
  }

  .verification-action {
    width: auto;
    min-width: 84px;
    padding: 0 9px;
    font-size: 11px;
  }

  .reset-complete {
    padding: 44px 24px 40px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .forgot-password-dialog-enter-active,
  .forgot-password-dialog-leave-active,
  .forgot-password-dialog-enter-active .forgot-password-dialog,
  .forgot-password-dialog-leave-active .forgot-password-dialog {
    transition-duration: 0.01ms !important;
  }
}
</style>
