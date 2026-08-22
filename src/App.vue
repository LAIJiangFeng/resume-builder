<!-- author: jf -->
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import LoginPage from '@/components/auth/LoginPage.vue'
import RegisterPage from '@/components/auth/RegisterPage.vue'
import KnowledgeBasePanel from '@/components/ai/knowledge/KnowledgeBasePanel.vue'
import AiInterviewerPanel from '@/components/ai/interview/AiInterviewerPanel.vue'
import ModuleSidebar from '@/components/common/ModuleSidebar.vue'
import EditorPanel from '@/components/resume/EditorPanel.vue'
import PreviewPanel from '@/components/resume/PreviewPanel.vue'
import AccountSettingsPanel from '@/components/settings/AccountSettingsPanel.vue'
import {
  DEFAULT_PRIMARY_MENU_KEY,
  isPrimaryMenuRoutePath,
  normalizePrimaryRoutePath,
  resolvePrimaryMenuFromPath,
  resolvePrimaryMenuPath,
  type PrimaryMenuKey,
} from '@/router/menuRoutes'
import { AUTH_SESSION_EXPIRED_EVENT } from '@/services/authService'
import { useAuthStore } from '@/stores/auth'
import { useResumeStore } from '@/stores/resume'

const sidebarCollapsed = ref(false)
const editorModuleSidebarCollapsed = ref(false)
const authStore = useAuthStore()
const resumeStore = useResumeStore()
type ResumeMobilePane = 'editor' | 'preview'
const activeMenu = ref<PrimaryMenuKey>(
  typeof window === 'undefined' ? DEFAULT_PRIMARY_MENU_KEY : resolvePrimaryMenuFromPath(window.location.pathname)
)
const activeResumePane = ref<ResumeMobilePane>('editor')
type ThemeMode = 'light' | 'porcelain-jade' | 'dark'
type AuthView = 'login' | 'register'
const THEME_STORAGE_KEY = 'resume-builder-theme'
const LOGIN_ROUTE_PATH = '/login'
const REGISTER_ROUTE_PATH = '/register'
const authView = ref<AuthView>(resolveInitialAuthView())
const themeMode = ref<ThemeMode>(resolveInitialThemeMode())
const isAuthenticated = computed(() => authStore.isAuthenticated)
const canManageKnowledgeBase = computed(() => authStore.canManageKnowledgeBase)

function resolveInitialAuthView(): AuthView {
  if (typeof window === 'undefined') return 'login'
  return normalizePrimaryRoutePath(window.location.pathname) === REGISTER_ROUTE_PATH ? 'register' : 'login'
}

function resolveInitialThemeMode(): ThemeMode {
  if (typeof window === 'undefined') return 'light'

  let storedMode: string | null = null
  try {
    storedMode = window.localStorage.getItem(THEME_STORAGE_KEY)
  } catch {
    storedMode = null
  }

  if (storedMode === 'dark' || storedMode === 'porcelain-jade') return storedMode
  return 'light'
}

function applyThemeMode(mode: ThemeMode = themeMode.value) {
  if (typeof document === 'undefined') return

  const root = document.documentElement
  root.dataset.theme = mode
  root.classList.toggle('dark', mode === 'dark')
  root.style.colorScheme = mode === 'dark' ? 'dark' : 'light'
}

function persistThemeMode(mode: ThemeMode) {
  if (typeof window === 'undefined') return

  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode)
  } catch {
    // 存储受限时仅保持当前页面主题，不阻断用户切换。
  }
}

function setThemeMode(mode: ThemeMode) {
  themeMode.value = mode
  applyThemeMode(mode)
  persistThemeMode(mode)
}

applyThemeMode(themeMode.value)

function setActiveMenu(key: PrimaryMenuKey) {
  const allowedKey = resolveAllowedMenuKey(key)
  activeMenu.value = allowedKey
  if (allowedKey === 'resume-editor') {
    activeResumePane.value = 'editor'
  }
}

function resolveAllowedMenuKey(key: PrimaryMenuKey): PrimaryMenuKey {
  if (key === 'knowledge-base' && !canManageKnowledgeBase.value) {
    return DEFAULT_PRIMARY_MENU_KEY
  }
  return key
}

function resolveAuthRoutePath(view: AuthView): string {
  return view === 'register' ? REGISTER_ROUTE_PATH : LOGIN_ROUTE_PATH
}

function setAuthView(view: AuthView, replace = false) {
  authView.value = view
  if (typeof window === 'undefined') return

  const targetPath = resolveAuthRoutePath(view)
  if (normalizePrimaryRoutePath(window.location.pathname) === targetPath) return

  const state = { auth: view }
  if (replace) {
    window.history.replaceState(state, '', targetPath)
    return
  }
  window.history.pushState(state, '', targetPath)
}

function syncAuthRoute(view: AuthView = authView.value) {
  setAuthView(view, true)
}

function syncLoginRoute() {
  syncAuthRoute('login')
}

function syncMenuFromLocation() {
  if (typeof window === 'undefined') return
  if (!isAuthenticated.value) {
    syncAuthRoute(resolveInitialAuthView())
    return
  }

  const key = resolveAllowedMenuKey(resolvePrimaryMenuFromPath(window.location.pathname))
  const targetPath = resolvePrimaryMenuPath(key)
  const currentPath = normalizePrimaryRoutePath(window.location.pathname)

  setActiveMenu(key)

  if (!isPrimaryMenuRoutePath(window.location.pathname) || currentPath !== targetPath) {
    window.history.replaceState({ primaryMenu: key }, '', targetPath)
  }
}

function handleSelectMenu(key: PrimaryMenuKey) {
  if (!isAuthenticated.value) {
    syncLoginRoute()
    return
  }

  setActiveMenu(key)

  if (typeof window === 'undefined') return

  const targetPath = resolvePrimaryMenuPath(resolveAllowedMenuKey(key))
  if (normalizePrimaryRoutePath(window.location.pathname) !== targetPath) {
    window.history.pushState({ primaryMenu: resolveAllowedMenuKey(key) }, '', targetPath)
  }
}

function handleLoginSuccess() {
  authView.value = 'login'
  setActiveMenu(DEFAULT_PRIMARY_MENU_KEY)
  if (typeof window !== 'undefined') {
    window.history.replaceState({ primaryMenu: DEFAULT_PRIMARY_MENU_KEY }, '', resolvePrimaryMenuPath(DEFAULT_PRIMARY_MENU_KEY))
  }
}

function handleShowRegister() {
  setAuthView('register')
}

function handleShowLogin() {
  setAuthView('login')
}

function handleLogout() {
  resumeStore.resetForLogout()
  authStore.logout()
  setActiveMenu(DEFAULT_PRIMARY_MENU_KEY)
  syncLoginRoute()
}

onMounted(() => {
  syncMenuFromLocation()
  if (isAuthenticated.value) {
    void resumeStore.initializeResumes().catch(() => undefined)
  }
  window.addEventListener('popstate', syncMenuFromLocation)
  window.addEventListener(AUTH_SESSION_EXPIRED_EVENT, handleLogout)
})

onUnmounted(() => {
  window.removeEventListener('popstate', syncMenuFromLocation)
  window.removeEventListener(AUTH_SESSION_EXPIRED_EVENT, handleLogout)
})

watch(
  () => authStore.isAuthenticated,
  (authenticated) => {
    if (authenticated) {
      syncMenuFromLocation()
      void resumeStore.initializeResumes().catch(() => undefined)
      return
    }
    resumeStore.resetForLogout()
    syncAuthRoute(resolveInitialAuthView())
  }
)

watch(
  () => authStore.currentUser?.id,
  (userId, previousUserId) => {
    if (!userId || !previousUserId || userId === previousUserId) return
    resumeStore.resetForLogout()
    void resumeStore.initializeResumes().catch(() => undefined)
  },
)
</script>

<template>
  <LoginPage
    v-if="!isAuthenticated && authView === 'login'"
    @login-success="handleLoginSuccess"
    @show-register="handleShowRegister"
  />
  <RegisterPage v-else-if="!isAuthenticated" @show-login="handleShowLogin" @register-success="handleLoginSuccess" />
  <div v-else class="app-layout">
    <ModuleSidebar
      :collapsed="sidebarCollapsed"
      :active-menu="activeMenu"
      :can-manage-knowledge-base="canManageKnowledgeBase"
      @toggle-collapse="sidebarCollapsed = !sidebarCollapsed"
      @select-menu="handleSelectMenu"
    />
    <div class="main-content">
      <section
        v-if="activeMenu === 'resume-editor'"
        class="resume-studio-page"
        :class="{ 'editor-module-sidebar-collapsed': editorModuleSidebarCollapsed }"
      >
        <div class="mobile-resume-tabs" role="tablist" aria-label="简历移动端视图切换">
          <button
            class="mobile-resume-tab"
            :class="{ active: activeResumePane === 'editor' }"
            type="button"
            role="tab"
            :aria-selected="activeResumePane === 'editor'"
            @click="activeResumePane = 'editor'"
          >
            编辑
          </button>
          <button
            class="mobile-resume-tab"
            :class="{ active: activeResumePane === 'preview' }"
            type="button"
            role="tab"
            :aria-selected="activeResumePane === 'preview'"
            @click="activeResumePane = 'preview'"
          >
            预览
          </button>
        </div>
        <EditorPanel
          class="resume-workspace-pane"
          :class="{ 'mobile-pane-hidden': activeResumePane !== 'editor' }"
          :module-sidebar-collapsed="editorModuleSidebarCollapsed"
          @toggle-module-sidebar="editorModuleSidebarCollapsed = !editorModuleSidebarCollapsed"
        />
        <PreviewPanel
          class="resume-workspace-pane"
          :class="{ 'mobile-pane-hidden': activeResumePane !== 'preview' }"
        />
      </section>
      <AiInterviewerPanel v-show="activeMenu === 'ai-interviewer'" />
      <KnowledgeBasePanel v-if="activeMenu === 'knowledge-base'" />
      <AccountSettingsPanel
        v-if="activeMenu === 'account-settings'"
        :theme-mode="themeMode"
        :current-user="authStore.currentUser"
        @set-theme="setThemeMode"
        @logout="handleLogout"
      />
    </div>
  </div>
</template>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  min-height: 100vh;
  overflow: hidden;
  background: var(--app-background);
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  min-width: 0;
  background: var(--app-background);
}

.mobile-resume-tabs {
  display: none;
}

.resume-studio-page {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-columns: 224px minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
  padding: 14px 14px 16px;
  overflow: hidden;
  transition: grid-template-columns 0.2s ease;
  background: transparent;
}

@media (min-width: 1281px) {
  .resume-studio-page.editor-module-sidebar-collapsed {
    grid-template-columns: 48px minmax(0, 1fr) minmax(0, 1fr);
  }
}

.resume-workspace-pane {
  min-width: 0;
  min-height: 0;
}

@media (min-width: 761px) and (max-width: 1280px) {
  .resume-studio-page {
    grid-template-columns: minmax(0, 1.1fr) minmax(300px, 0.9fr);
  }
}

@supports (height: 100dvh) {
  .app-layout {
    height: 100dvh;
    min-height: 100dvh;
  }
}

@media (max-width: 760px) {
  .app-layout {
    height: 100dvh;
    min-height: 100dvh;
    padding-bottom: calc(74px + env(safe-area-inset-bottom));
    background: var(--bg-app);
  }

  .main-content {
    position: relative;
    flex-direction: column;
    height: 100%;
    min-height: 0;
    overflow: hidden;
  }

  .resume-studio-page {
    display: flex;
    flex-direction: column;
    gap: 0;
    height: 100%;
    padding: 0;
    overflow: hidden;
  }

  .mobile-resume-tabs {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 5px;
    padding: 7px 8px 6px;
    background: var(--mobile-nav-background);
    border-bottom: 1px solid var(--sidebar-border);
    flex-shrink: 0;
    z-index: 4;
  }

  .mobile-resume-tab {
    min-height: 34px;
    border: 1px solid var(--border-color);
    border-radius: 12px;
    background: var(--surface-base);
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 800;
  }

  .mobile-resume-tab.active {
    border-color: var(--primary-500);
    background: var(--primary-500);
    color: var(--text-inverse);
    box-shadow: var(--shadow-brand);
  }

  .resume-workspace-pane {
    flex: 1 1 auto;
    min-height: 0;
    width: 100%;
  }

  .mobile-pane-hidden {
    display: none !important;
  }
}
</style>
