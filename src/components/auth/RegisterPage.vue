<!-- author: jf -->
<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import {
  ArrowLeft,
  CheckCircle2,
  Eye,
  EyeOff,
  FilePenLine,
  LockKeyhole,
  Mail,
  ShieldCheck,
  UserRound,
} from 'lucide-vue-next'
import TermsDialog from '@/components/auth/TermsDialog.vue'
import { useAuthStore } from '@/stores/auth'

const emit = defineEmits<{
  (e: 'show-login'): void
  (e: 'register-success'): void
}>()

const authStore = useAuthStore()
const fullName = ref('')
const email = ref('')
const verificationCode = ref('')
const password = ref('')
const confirmPassword = ref('')
const acceptedTerms = ref(false)
const isTermsDialogOpen = ref(false)
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const errorMessage = ref('')
const statusMessage = ref('')
const isSubmitting = ref(false)
const isSendingCode = ref(false)
const cooldownSeconds = ref(0)
let cooldownTimer: ReturnType<typeof setInterval> | null = null

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

const passwordStrength = computed(() => {
  const value = password.value
  if (value.length >= 10 && /[A-Za-z]/.test(value) && /\d/.test(value)) return '强'
  if (value.length >= 8) return '中'
  return '弱'
})
const passwordStrengthTone = computed(() => {
  if (passwordStrength.value === '强') return 'strong'
  if (passwordStrength.value === '中') return 'medium'
  return 'weak'
})
const emailCodeButtonLabel = computed(() => {
  if (isSendingCode.value) return '发送中...'
  if (cooldownSeconds.value > 0) return `${cooldownSeconds.value}s 后重发`
  return '发送验证码'
})

function resetFeedback() {
  errorMessage.value = ''
  statusMessage.value = ''
}

function acceptTermsAndCloseDialog() {
  acceptedTerms.value = true
  isTermsDialogOpen.value = false
  resetFeedback()
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

function handleEmailInput() {
  resetFeedback()
  verificationCode.value = ''
  cooldownSeconds.value = 0
  clearCooldownTimer()
}

function handleVerificationCodeInput(event: Event) {
  const target = event.target as HTMLInputElement
  const normalizedCode = target.value.replace(/\D/g, '').slice(0, 6)
  target.value = normalizedCode
  verificationCode.value = normalizedCode
  resetFeedback()
}

function isEmailValid() {
  return EMAIL_PATTERN.test(email.value.trim())
}

async function handleSendEmailCode() {
  if (isSendingCode.value || isSubmitting.value || cooldownSeconds.value > 0) return
  resetFeedback()

  if (!isEmailValid()) {
    errorMessage.value = '请输入正确的邮箱地址。'
    return
  }

  const requestedEmail = email.value.trim().toLowerCase()
  isSendingCode.value = true
  statusMessage.value = '正在发送邮箱验证码...'
  try {
    const result = await authStore.sendRegistrationEmailCode(requestedEmail)
    startCooldown(result.cooldownSeconds)
    const validMinutes = Math.max(1, Math.ceil(result.expiresInSeconds / 60))
    statusMessage.value = `验证码已发送至 ${requestedEmail}，${validMinutes} 分钟内有效。`
  } catch (error) {
    const message = error instanceof Error ? error.message : '验证码发送服务不可用，请稍后重试。'
    statusMessage.value = ''
    errorMessage.value = `验证码发送失败：${message}`
  } finally {
    isSendingCode.value = false
  }
}

onBeforeUnmount(clearCooldownTimer)

async function handleSubmit() {
  if (isSubmitting.value || isSendingCode.value) return
  resetFeedback()

  if (
    !fullName.value.trim() ||
    !email.value.trim() ||
    !verificationCode.value ||
    !password.value ||
    !confirmPassword.value
  ) {
    errorMessage.value = '请填写完整注册信息。'
    return
  }

  if (!isEmailValid()) {
    errorMessage.value = '请输入正确的邮箱地址。'
    return
  }

  if (!/^\d{6}$/.test(verificationCode.value)) {
    errorMessage.value = '请输入 6 位邮箱验证码。'
    return
  }

  if (password.value.length < 8) {
    errorMessage.value = '密码至少需要 8 位。'
    return
  }

  if (password.value !== confirmPassword.value) {
    errorMessage.value = '两次输入的密码不一致。'
    return
  }

  if (!acceptedTerms.value) {
    errorMessage.value = '请先勾选服务条款。'
    return
  }

  isSubmitting.value = true
  statusMessage.value = '正在创建账号...'
  try {
    if (await authStore.register(fullName.value, email.value, verificationCode.value, password.value)) {
      statusMessage.value = '注册成功，正在进入工作台。'
      emit('register-success')
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : '注册服务不可用，请稍后重试。'
    statusMessage.value = ''
    errorMessage.value = `注册失败：${message}`
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <main class="register-page">
    <section class="register-stage" aria-labelledby="register-title">
      <aside class="register-visual" aria-label="Resume Studio">
        <div class="brand-lockup">
          <span class="brand-icon" aria-hidden="true">
            <FilePenLine :size="20" stroke-width="1.9" />
          </span>
          <div>
            <strong>Resume Studio</strong>
            <span>简历编辑工作台</span>
          </div>
        </div>

        <div class="resume-preview-card" aria-hidden="true">
          <div class="preview-head">
            <span></span>
            <i></i>
          </div>
          <div class="preview-body">
            <div class="preview-profile">
              <span></span>
              <strong></strong>
              <i></i>
              <i></i>
            </div>
            <div class="preview-lines">
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      </aside>

      <div class="auth-column">
        <form class="register-card" :aria-busy="isSubmitting || isSendingCode" @submit.prevent="handleSubmit">
          <button class="back-link" type="button" @click="emit('show-login')">
            <ArrowLeft :size="17" stroke-width="1.9" aria-hidden="true" />
            返回登录
          </button>

          <div class="register-heading">
            <h1 id="register-title">创建账号</h1>
          </div>

          <div class="register-form-fields">
            <div class="field-shell">
              <label class="sr-only" for="register-name">姓名</label>
              <UserRound :size="20" stroke-width="1.8" aria-hidden="true" />
              <input
                id="register-name"
                v-model.trim="fullName"
                type="text"
                autocomplete="name"
                placeholder="姓名"
                @input="resetFeedback"
              />
            </div>

            <div class="field-shell">
              <label class="sr-only" for="register-email">邮箱</label>
              <Mail :size="20" stroke-width="1.8" aria-hidden="true" />
              <input
                id="register-email"
                v-model.trim="email"
                type="email"
                autocomplete="email"
                maxlength="254"
                placeholder="邮箱"
                :disabled="isSendingCode || isSubmitting"
                @input="handleEmailInput"
              />
            </div>

            <div class="field-shell verification-field">
              <label class="sr-only" for="register-verification-code">邮箱验证码</label>
              <ShieldCheck :size="20" stroke-width="1.8" aria-hidden="true" />
              <input
                id="register-verification-code"
                v-model="verificationCode"
                type="text"
                inputmode="numeric"
                autocomplete="one-time-code"
                maxlength="6"
                placeholder="6 位验证码"
                @input="handleVerificationCodeInput"
              />
              <button
                class="verification-action"
                type="button"
                :disabled="isSendingCode || isSubmitting || cooldownSeconds > 0"
                :aria-label="emailCodeButtonLabel"
                :aria-busy="isSendingCode"
                @click="handleSendEmailCode"
              >
                {{ emailCodeButtonLabel }}
              </button>
            </div>

            <div class="field-shell">
              <label class="sr-only" for="register-password">密码</label>
              <LockKeyhole :size="20" stroke-width="1.8" aria-hidden="true" />
              <input
                id="register-password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="new-password"
                placeholder="密码"
                @input="resetFeedback"
              />
              <button
                class="password-toggle"
                type="button"
                :aria-label="showPassword ? '隐藏密码' : '显示密码'"
                @click="showPassword = !showPassword"
              >
                <Eye v-if="showPassword" :size="18" stroke-width="1.9" aria-hidden="true" />
                <EyeOff v-else :size="18" stroke-width="1.9" aria-hidden="true" />
              </button>
            </div>

            <div class="field-shell">
              <label class="sr-only" for="register-confirm-password">确认密码</label>
              <LockKeyhole :size="20" stroke-width="1.8" aria-hidden="true" />
              <input
                id="register-confirm-password"
                v-model="confirmPassword"
                :type="showConfirmPassword ? 'text' : 'password'"
                autocomplete="new-password"
                placeholder="确认密码"
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
          </div>

          <div class="register-meta">
            <span>密码强度：</span>
            <strong class="strength-value" :class="`strength-${passwordStrengthTone}`">{{ passwordStrength }}</strong>
          </div>

          <div class="terms-option">
            <input id="register-terms" v-model="acceptedTerms" type="checkbox" @change="resetFeedback" />
            <div class="terms-copy">
              <label class="terms-consent-label" for="register-terms">我已阅读并同意</label>
              <button class="terms-link" type="button" @click="isTermsDialogOpen = true">
                《Resume Studio 服务条款》
              </button>
            </div>
          </div>

          <p v-if="errorMessage" class="register-error" role="alert">{{ errorMessage }}</p>
          <p v-if="statusMessage" class="register-status" role="status" aria-live="polite">
            <CheckCircle2
              v-if="!isSubmitting && !isSendingCode"
              :size="16"
              stroke-width="1.9"
              aria-hidden="true"
            />
            <span>{{ statusMessage }}</span>
          </p>

          <button class="register-submit" type="submit" :disabled="isSubmitting">
            <span>{{ isSubmitting ? '创建中...' : '创建账号' }}</span>
          </button>

          <div class="register-footer">
            <span>已有账号？</span>
            <button class="login-link" type="button" @click="emit('show-login')">登录</button>
          </div>
        </form>
      </div>
    </section>
    <TermsDialog
      :open="isTermsDialogOpen"
      @close="isTermsDialogOpen = false"
      @accept="acceptTermsAndCloseDialog"
    />
  </main>
</template>

<style scoped>
.register-page {
  --page-bg: var(--bg-app);
  --paper: var(--surface-base);
  --paper-soft: var(--surface-soft);
  --line: var(--border-color);
  --line-soft: var(--border-soft);
  --text-main: var(--text-primary);
  --text-muted: var(--text-secondary);
  --text-soft: var(--text-tertiary);
  --primary: var(--primary-500);
  --primary-soft: color-mix(in srgb, var(--primary-500) 8%, transparent);
  --primary-tint: var(--primary-50);
  --success: var(--text-success-strong);
  --success-soft: var(--accent-green-soft);
  --error: var(--text-danger);

  min-height: 100vh;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  isolation: isolate;
  overflow-x: hidden;
  overflow-y: auto;
  padding: clamp(24px, 4vw, 70px);
  background: var(--app-background);
  color: var(--text-main);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
}

.register-stage {
  width: min(100%, 1080px);
  min-height: min(820px, calc(100vh - 70px));
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(380px, 440px);
  align-items: center;
  gap: clamp(44px, 7vw, 96px);
}

.register-visual,
.auth-column {
  min-width: 0;
}

.brand-lockup,
.back-link,
.field-shell,
.password-toggle,
.terms-option,
.register-status,
.register-submit {
  display: flex;
  align-items: center;
}

.brand-lockup {
  gap: 14px;
  margin-bottom: 34px;
}

.brand-icon {
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  border: 1px solid var(--theme-toggle-border);
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--primary);
  background: var(--primary-soft);
}

.brand-lockup strong {
  display: block;
  color: var(--text-main);
  font-size: 18px;
  font-weight: 650;
  line-height: 1.35;
}

.brand-lockup span:not(.brand-icon) {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 400;
  line-height: 1.35;
}

.resume-preview-card {
  width: min(100%, 560px);
  border: 1px solid var(--line);
  border-radius: 32px;
  overflow: hidden;
  background: var(--surface-translucent);
  box-shadow: var(--shadow-xl);
}

.preview-head {
  height: 58px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 0 28px;
  border-bottom: 1px solid var(--line-soft);
}

.preview-head span,
.preview-head i,
.preview-profile strong,
.preview-profile i,
.preview-lines span {
  display: block;
  border-radius: 999px;
  background: var(--skeleton-fill);
}

.preview-head span {
  width: 154px;
  height: 13px;
}

.preview-head i {
  width: 92px;
  height: 26px;
  background: var(--primary-tint);
}

.preview-body {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 28px;
  padding: 28px;
}

.preview-profile {
  min-height: 232px;
  padding: 24px;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: var(--paper);
}

.preview-profile span {
  width: 54px;
  height: 54px;
  display: block;
  margin-bottom: 28px;
  border-radius: 18px;
  background: var(--primary-tint);
}

.preview-profile strong {
  width: 92px;
  height: 18px;
  margin-bottom: 18px;
  background: var(--text-main);
}

.preview-profile i {
  width: 100%;
  height: 10px;
  margin-top: 10px;
}

.preview-profile i:last-child {
  width: 72%;
}

.preview-lines {
  display: grid;
  gap: 16px;
  align-content: center;
}

.preview-lines span {
  height: 14px;
}

.preview-lines span:nth-child(2) {
  width: 82%;
}

.preview-lines span:nth-child(3) {
  width: 92%;
}

.preview-lines span:nth-child(4) {
  width: 68%;
}

.auth-column {
  display: flex;
  justify-content: center;
}

.register-card {
  width: min(100%, 440px);
  padding: clamp(30px, 3.2vw, 42px);
  border: 1px solid var(--line);
  border-radius: 32px;
  background: var(--paper);
  box-shadow: var(--shadow-card);
}

.back-link,
.login-link {
  border: 0;
  background: transparent;
  color: var(--primary);
  cursor: pointer;
  font: inherit;
}

.back-link {
  gap: 7px;
  width: max-content;
  margin-bottom: 30px;
  padding: 0;
  font-size: 14px;
  font-weight: 500;
}

.register-heading {
  margin-bottom: 28px;
}

.register-heading h1 {
  margin: 0;
  color: var(--text-main);
  font-size: clamp(25px, 2.35vw, 32px);
  font-weight: 650;
  letter-spacing: -0.02em;
  line-height: 1.28;
}

.register-form-fields {
  display: grid;
  gap: 16px;
}

.field-shell {
  height: 56px;
  gap: 12px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--paper-soft);
  color: var(--text-muted);
  padding: 0 18px;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background-color 0.18s ease;
}

.field-shell:focus-within {
  border-color: var(--primary);
  background: var(--paper-soft);
  box-shadow: 0 0 0 3px var(--theme-focus-ring);
}

.field-shell input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text-main);
  font: inherit;
  font-size: 15px;
  font-weight: 350;
}

.field-shell input::placeholder {
  color: var(--text-muted);
}

.password-toggle {
  justify-content: center;
  flex: 0 0 auto;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
  transition:
    color 0.18s ease,
    background-color 0.18s ease;
}

.verification-field {
  padding-right: 9px;
}

.verification-action {
  min-width: 98px;
  height: 38px;
  flex: 0 0 auto;
  border: 0;
  border-radius: 11px;
  background: var(--primary-soft);
  color: var(--primary);
  cursor: pointer;
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  transition:
    color 0.18s ease,
    background-color 0.18s ease,
    opacity 0.18s ease;
}

.verification-action:not(:disabled):hover,
.verification-action:focus-visible {
  background: var(--primary);
  color: var(--text-inverse);
}

.verification-action:disabled {
  opacity: 0.56;
  cursor: not-allowed;
}

.password-toggle:hover,
.password-toggle:focus-visible {
  color: var(--text-main);
  background: var(--primary-soft);
}

.register-meta {
  display: flex;
  align-items: center;
  gap: 2px;
  margin: 12px 0 0;
  color: var(--text-soft);
  font-size: 12px;
  font-weight: 350;
}

.strength-value {
  font-weight: 650;
  letter-spacing: 0.02em;
}

.strength-weak {
  color: var(--text-warning);
}

.strength-medium {
  color: var(--text-warning-soft);
}

.strength-strong {
  color: var(--success);
}

.terms-option {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr);
  align-items: start;
  gap: 9px;
  margin-top: 18px;
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 350;
}

.terms-option input {
  width: 16px;
  height: 16px;
  flex: 0 0 auto;
  margin-top: 3px;
  accent-color: var(--primary);
  cursor: pointer;
}

.terms-copy {
  min-width: 0;
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  line-height: 1.6;
  white-space: nowrap;
}

.terms-consent-label {
  cursor: pointer;
}

.terms-link {
  display: inline;
  margin: 0 0 0 3px;
  padding: 2px 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  font-weight: 500;
  text-underline-offset: 4px;
  cursor: pointer;
  transition: color 0.18s ease;
}

.terms-link:hover,
.terms-link:focus-visible {
  color: var(--primary);
  text-decoration: underline;
}

.register-error,
.register-status {
  margin: 16px 0 0;
  font-size: 13px;
  line-height: 1.5;
}

.register-error {
  color: var(--error);
  font-weight: 600;
}

.register-status {
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid var(--border-success);
  border-radius: 14px;
  background: var(--success-soft);
  color: var(--success);
  font-weight: 500;
}

.register-status svg {
  flex: 0 0 auto;
}

.register-status span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.register-submit {
  height: 56px;
  width: 100%;
  justify-content: center;
  gap: 10px;
  margin-top: 20px;
  border: 0;
  border-radius: 16px;
  background: var(--primary);
  color: var(--text-inverse);
  font-size: 16px;
  font-weight: 650;
  cursor: pointer;
  transition:
    opacity 0.18s ease,
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.register-submit:hover,
.register-submit:focus-visible {
  opacity: 0.94;
  transform: translateY(-1px);
  box-shadow: var(--shadow-brand);
}

.register-submit:disabled {
  opacity: 0.58;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.register-footer {
  margin-top: 28px;
  text-align: center;
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 350;
}

.login-link {
  margin-left: 4px;
  font-size: 14px;
  font-weight: 500;
  text-underline-offset: 4px;
}

.back-link:hover,
.back-link:focus-visible,
.login-link:hover,
.login-link:focus-visible {
  text-decoration: underline;
}

.back-link:focus-visible,
.login-link:focus-visible,
.password-toggle:focus-visible,
.verification-action:focus-visible,
.terms-link:focus-visible,
.register-submit:focus-visible {
  outline: 2px solid var(--primary);
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

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
  }
}

@media (max-width: 980px) {
  .register-page {
    align-items: flex-start;
    background: var(--app-background);
  }

  .register-stage {
    width: 100%;
    max-width: 100%;
    min-height: auto;
    grid-template-columns: minmax(0, 1fr);
    gap: 26px;
  }

  .register-visual,
  .auth-column {
    width: min(100%, 560px);
    margin: 0 auto;
  }

  .resume-preview-card {
    width: 100%;
  }
}

@media (max-width: 620px) {
  .register-page {
    min-height: 100dvh;
    padding: 22px 22px 20px;
    background: var(--app-background);
  }

  .register-stage,
  .register-visual,
  .auth-column {
    width: 100%;
    max-width: 100%;
  }

  .register-card {
    width: min(100%, 344px);
    max-width: 100%;
  }

  .auth-column {
    justify-content: flex-start;
  }

  .brand-lockup {
    gap: 12px;
    margin-bottom: 20px;
  }

  .brand-icon {
    width: 40px;
    height: 40px;
    border-radius: 13px;
    border-color: var(--line);
    background: var(--paper);
  }

  .resume-preview-card {
    display: none;
  }

  .register-card {
    padding: 26px;
    border-radius: 26px;
  }

  .register-heading h1 {
    font-size: 24px;
  }

  .field-shell,
  .register-submit {
    height: 52px;
    border-radius: 15px;
  }

  .verification-action {
    min-width: 94px;
    height: 36px;
    font-size: 12px;
  }

  .terms-option {
    grid-template-columns: 16px minmax(0, 1fr);
    gap: 7px;
    font-size: 13px;
  }

  .terms-link {
    margin-left: 2px;
  }
}
</style>
