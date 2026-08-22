<!-- author: jf -->
<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  Bot,
  CheckCircle2,
  ChevronDown,
  Eye,
  EyeOff,
  FilePenLine,
  LockKeyhole,
  Mail,
} from 'lucide-vue-next'
import ForgotPasswordDialog from '@/components/auth/ForgotPasswordDialog.vue'
import { LOGIN_ACCOUNT_OPTIONS } from '@/services/authService'
import { useAuthStore } from '@/stores/auth'

const emit = defineEmits<{
  (e: 'login-success'): void
  (e: 'show-register'): void
}>()

const authStore = useAuthStore()
const username = ref('')
const password = ref('')
const errorMessage = ref('')
const statusMessage = ref('')
const isSubmitting = ref(false)
const isForgotPasswordOpen = ref(false)
const rememberMe = ref(true)
const showPassword = ref(false)

const selectedAccount = computed(() => LOGIN_ACCOUNT_OPTIONS.find((account) => account.username === username.value))
const selectedRoleLabel = computed(() => (selectedAccount.value?.role === 'admin' ? '管理员' : '普通用户'))

function fillAccount(account: (typeof LOGIN_ACCOUNT_OPTIONS)[number]) {
  username.value = account.username
  password.value = account.password
  errorMessage.value = ''
  statusMessage.value = ''
}

function openForgotPasswordDialog() {
  errorMessage.value = ''
  statusMessage.value = ''
  isForgotPasswordOpen.value = true
}

function handlePasswordResetSuccess(resetEmail: string) {
  username.value = resetEmail
  password.value = ''
  errorMessage.value = ''
  statusMessage.value = '密码已重置，请使用新密码登录。'
  isForgotPasswordOpen.value = false
}

async function handleSubmit() {
  if (isSubmitting.value) return
  errorMessage.value = ''
  statusMessage.value = ''
  if (!username.value.trim()) {
    errorMessage.value = '请输入邮箱或管理员账号。'
    return
  }
  if (!password.value) {
    errorMessage.value = '请输入密码。'
    return
  }
  isSubmitting.value = true
  try {
    if (await authStore.login(username.value, password.value)) {
      emit('login-success')
      return
    }
    errorMessage.value = '账号或密码不正确，请检查输入或使用演示账号后重试。'
  } catch (error) {
    const message = error instanceof Error ? error.message : '登录服务不可用'
    errorMessage.value = `登录失败：${message}`
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-stage" aria-labelledby="login-title">
      <div class="auth-column">
        <div class="login-card">
          <div class="brand-lockup" aria-label="Resume Studio">
            <span class="brand-icon" aria-hidden="true">
              <FilePenLine :size="20" stroke-width="1.9" />
            </span>
            <div>
              <strong>Resume Studio</strong>
              <span>简历编辑工作台</span>
            </div>
          </div>

          <div class="login-heading">
            <h2 id="login-title">登录简历工作台</h2>
          </div>

          <form class="login-form" @submit.prevent="handleSubmit">
            <div class="field-shell">
              <label class="sr-only" for="login-username">邮箱 / 管理员账号</label>
              <Mail :size="20" stroke-width="1.8" aria-hidden="true" />
              <input
                id="login-username"
                v-model.trim="username"
                type="text"
                autocomplete="username"
                placeholder="邮箱 / 管理员账号"
              />
            </div>

            <div class="field-shell">
              <label class="sr-only" for="login-password">密码</label>
              <LockKeyhole :size="20" stroke-width="1.8" aria-hidden="true" />
              <input
                id="login-password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                placeholder="密码"
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

            <div class="login-actions-row">
              <label class="remember-option">
                <input v-model="rememberMe" type="checkbox" />
                <span>记住我</span>
              </label>
              <button class="text-link" type="button" @click="openForgotPasswordDialog">忘记密码？</button>
            </div>

            <p v-if="selectedAccount" class="account-hint">
              当前演示身份：{{ selectedAccount.displayName }} · {{ selectedRoleLabel }}
            </p>
            <p v-if="errorMessage" class="login-error" aria-live="polite">{{ errorMessage }}</p>
            <p v-if="statusMessage" class="login-status" role="status" aria-live="polite">
              <CheckCircle2 :size="16" stroke-width="1.9" aria-hidden="true" />
              <span>{{ statusMessage }}</span>
            </p>

            <button class="login-submit" type="submit" :disabled="isSubmitting">
              <span>{{ isSubmitting ? '登录中...' : '登录' }}</span>
            </button>
          </form>

          <div class="login-footer">
            <span>还没有账号？</span>
            <button class="register-link" type="button" @click="emit('show-register')">创建账号</button>
          </div>

          <details class="demo-accounts">
            <summary>
              <span>
                <Bot :size="16" stroke-width="1.9" aria-hidden="true" />
                查看演示账号
              </span>
              <CheckCircle2 v-if="selectedAccount" :size="16" stroke-width="1.9" aria-hidden="true" />
              <ChevronDown v-else :size="18" stroke-width="1.9" aria-hidden="true" />
            </summary>
            <div class="account-options" aria-label="演示账号">
              <button
                v-for="account in LOGIN_ACCOUNT_OPTIONS"
                :key="account.username"
                class="account-option"
                type="button"
                :class="{ active: username === account.username }"
                @click="fillAccount(account)"
              >
                <span>{{ account.role === 'admin' ? '管理员' : '普通用户' }}</span>
                <strong>{{ account.username }} / {{ account.password }}</strong>
              </button>
            </div>
          </details>

        </div>
      </div>
    </section>
    <ForgotPasswordDialog
      :open="isForgotPasswordOpen"
      :initial-email="username"
      @close="isForgotPasswordOpen = false"
      @reset-success="handlePasswordResetSuccess"
    />
  </main>
</template>

<style scoped>
.login-page {
  --page-bg: var(--bg-app);
  --right-panel: var(--bg-sidebar);
  --paper: var(--surface-base);
  --paper-soft: var(--surface-soft);
  --paper-muted: var(--surface-disabled);
  --line: var(--border-color);
  --line-soft: var(--border-soft);
  --text-main: var(--text-primary);
  --text-muted: var(--text-secondary);
  --text-soft: var(--text-tertiary);
  --primary: var(--primary-500);
  --primary-soft: color-mix(in srgb, var(--primary-500) 8%, transparent);
  --primary-tint: var(--primary-50);
  --paper-line: var(--border-soft);
  --paper-line-strong: var(--border-neutral);

  min-height: 100vh;
  width: 100%;
  max-width: 100vw;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  isolation: isolate;
  overflow-x: hidden;
  overflow-y: auto;
  padding: clamp(24px, 4vw, 70px);
  background: var(--app-background);
  color: var(--text-main);
  font-family: var(--font-sans);
  -webkit-font-smoothing: antialiased;
}

.login-stage {
  width: min(100%, 430px);
  min-height: min(900px, calc(100vh - 70px));
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  align-items: center;
  justify-content: center;
  gap: 0;
  position: relative;
}

.story-column,
.auth-column { min-width: 0; }

.story-inner {
  width: min(100%, 720px);
  margin-right: auto;
}

.brand-lockup,
.readiness-head,
.readiness-head span,
.login-actions-row,
.remember-option,
.demo-accounts summary,
.demo-accounts summary span,
.login-submit {
  display: flex;
  align-items: center;
}

.brand-lockup {
  gap: 14px;
  margin-bottom: 26px;
}

.brand-icon {
  color: var(--primary);
  background: var(--primary-soft);
  border: 1px solid var(--theme-toggle-border);
}

.brand-icon {
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
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

.story-copy {
  margin-bottom: clamp(42px, 5vw, 66px);
}

.story-copy h1 {
  width: min(100%, 680px);
  margin: 0 0 18px;
  color: var(--text-main);
  font-size: clamp(36px, 4vw, 54px);
  font-weight: 650;
  letter-spacing: -0.03em;
  line-height: 1.12;
}

.story-copy p,
.login-heading p,
.login-footer,
.account-hint,
.safety-hint {
  color: var(--text-muted);
}

.story-copy p {
  width: min(100%, 548px);
  margin: 0;
  font-size: clamp(16px, 1.45vw, 20px);
  font-weight: 350;
  line-height: 1.55;
}

.readiness-card {
  width: min(100%, 420px);
  padding: 22px 24px;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: var(--paper);
  box-shadow: var(--shadow-lg);
}

.readiness-head {
  justify-content: space-between;
  gap: 18px;
}

.readiness-head span {
  gap: 10px;
  color: var(--text-main);
  font-size: 14px;
  font-weight: 500;
}

.readiness-head svg {
  color: var(--text-success-strong);
}

.readiness-head strong {
  color: var(--primary);
  font-size: 30px;
  font-weight: 650;
  line-height: 1;
}

.readiness-track {
  height: 8px;
  margin-top: 18px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--skeleton-fill);
}

.readiness-track span {
  display: block;
  width: 76%;
  height: 100%;
  border-radius: inherit;
  background: var(--primary);
}

.readiness-card p {
  margin: 12px 0 0;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 350;
  line-height: 1.4;
}

.feature-cards {
  width: min(100%, 578px);
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-top: 34px;
}

.feature-cards article {
  min-height: 128px;
  padding: 18px;
  border: 1px solid var(--line);
  border-radius: 22px;
  background: var(--surface-glass);
  box-shadow: var(--shadow-md);
}

.feature-cards svg {
  color: var(--primary);
}

.feature-cards strong {
  display: block;
  margin-top: 12px;
  color: var(--text-main);
  font-size: 15px;
  font-weight: 600;
  line-height: 1.2;
}

.feature-cards p {
  margin: 8px 0 0;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 350;
  line-height: 1.45;
}

.auth-column {
  display: flex;
  justify-content: center;
}

.login-card {
  width: min(100%, 430px);
  padding: clamp(30px, 3.2vw, 42px);
  border: 1px solid var(--line);
  border-radius: 32px;
  background: var(--paper);
  box-shadow: var(--shadow-card);
}

.login-heading {
  margin-bottom: 30px;
}

.login-heading h2 {
  margin: 0 0 12px;
  color: var(--text-main);
  font-size: clamp(25px, 2.35vw, 32px);
  font-weight: 650;
  letter-spacing: -0.02em;
  line-height: 1.28;
}

.login-heading p {
  margin: 0;
  font-size: 15px;
  font-weight: 350;
  line-height: 1.48;
}

.login-form { display: grid; gap: 16px; }

.field-shell {
  height: 56px;
  display: flex;
  align-items: center;
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

.password-toggle,
.text-link,
.register-link {
  border: 0;
  background: transparent;
  cursor: pointer;
  font: inherit;
}

.password-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  color: var(--text-muted);
  padding: 4px;
  border-radius: 8px;
  transition:
    color 0.18s ease,
    background-color 0.18s ease;
}

.password-toggle:hover,
.password-toggle:focus-visible {
  color: var(--text-main);
  background: var(--primary-soft);
}

.login-actions-row {
  justify-content: space-between;
  gap: 16px;
  padding: 4px 0 8px;
}

.remember-option {
  gap: 8px;
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 350;
  cursor: pointer;
}

.remember-option input {
  width: 16px;
  height: 16px;
  accent-color: var(--primary);
  cursor: pointer;
}

.text-link,
.register-link {
  color: var(--primary);
  font-size: 14px;
  font-weight: 500;
  text-underline-offset: 4px;
}

.text-link:hover,
.register-link:hover,
.text-link:focus-visible,
.register-link:focus-visible {
  text-decoration: underline;
}

.account-hint,
.login-error,
.login-status {
  margin: -2px 0 0;
  font-size: 13px;
  font-weight: 350;
  line-height: 1.5;
}

.login-error {
  color: var(--text-danger);
  font-weight: 600;
}

.login-status {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-success-strong);
  font-weight: 600;
}

.login-submit {
  height: 56px;
  width: 100%;
  justify-content: center;
  gap: 10px;
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

.login-submit:hover,
.login-submit:focus-visible {
  opacity: 0.94;
  transform: translateY(-1px);
  box-shadow: var(--shadow-brand);
}

.login-submit:disabled {
  opacity: 0.58;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.login-footer {
  margin-top: 28px;
  text-align: center;
  font-size: 14px;
  font-weight: 350;
}

.register-link {
  margin-left: 4px;
}

.demo-accounts {
  margin-top: 28px;
  border-top: 1px solid var(--line-soft);
}

.demo-accounts summary {
  justify-content: space-between;
  gap: 12px;
  padding: 20px 0 12px;
  color: var(--primary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  list-style: none;
}

.demo-accounts summary::-webkit-details-marker { display: none; }

.demo-accounts summary span { gap: 8px; }
.demo-accounts summary svg { color: var(--primary); }

.account-options {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
  padding: 0 0 10px;
}

.account-option {
  min-width: 0;
  display: grid;
  gap: 4px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--paper-soft);
  color: var(--text-main);
  padding: 10px 12px;
  text-align: left;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    background-color 0.18s ease,
    transform 0.18s ease;
}

.account-option span {
  color: var(--text-soft);
  font-size: 12px;
  font-weight: 350;
}

.account-option strong {
  overflow: hidden;
  color: var(--text-main);
  font-size: 12px;
  font-weight: 650;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-option:hover,
.account-option.active {
  border-color: var(--primary);
  background: var(--primary-soft);
  transform: translateY(-1px);
}

.safety-hint {
  margin: 12px 0 0;
  font-size: 12px;
  font-weight: 350;
  line-height: 1.45;
}

.field-shell:focus-visible,
.password-toggle:focus-visible,
.text-link:focus-visible,
.register-link:focus-visible,
.login-submit:focus-visible,
.account-option:focus-visible,
.demo-accounts summary:focus-visible {
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
  .login-page {
    align-items: center;
    background: var(--app-background);
  }

  .login-stage {
    min-height: calc(100dvh - 48px);
    grid-template-columns: 1fr;
    gap: 0;
  }

  .story-inner,
  .auth-column {
    width: min(100%, 560px);
    margin: 0 auto;
  }

  .auth-column {
    justify-content: center;
  }

  .brand-lockup {
    margin-bottom: 24px;
  }

  .story-copy {
    margin-bottom: 26px;
  }

  .readiness-card,
  .feature-cards {
    width: 100%;
  }
}

@media (max-width: 620px) {
  .login-page {
    align-items: center;
    min-height: 100dvh;
    padding: 22px 22px 20px;
    background: var(--app-background);
  }

  .login-stage {
    min-height: calc(100dvh - 42px);
    align-items: center;
    gap: 0;
  }

  .brand-lockup {
    gap: 12px;
    margin-bottom: 24px;
  }

  .brand-icon {
    width: 40px;
    height: 40px;
    border-radius: 13px;
    border-color: var(--line);
    background: var(--paper);
  }

  .brand-lockup strong,
  .story-copy h1 {
    color: var(--text-main);
  }

  .brand-lockup span:not(.brand-icon),
  .story-copy p {
    color: var(--text-muted);
  }

  .story-copy h1 {
    font-size: 30px;
    line-height: 1.18;
  }

  .story-copy p { font-size: 14px; }

  .story-copy { margin-bottom: 46px; }

  .readiness-card {
    margin-top: -4px;
    padding: 18px;
    border-radius: 20px;
  }

  .readiness-head strong {
    font-size: 22px;
  }

  .feature-cards {
    display: none;
  }

  .login-card {
    margin: 0;
    padding: 26px;
    border-radius: 26px;
  }

  .brand-lockup {
    margin-bottom: 24px;
  }

  .login-heading h2 {
    font-size: 24px;
  }

  .field-shell,
  .login-submit {
    height: 52px;
    border-radius: 15px;
  }

  .login-actions-row {
    align-items: center;
    justify-content: space-between;
    flex-direction: row;
    white-space: nowrap;
  }

  .account-options {
    grid-template-columns: 1fr;
  }
}
</style>
